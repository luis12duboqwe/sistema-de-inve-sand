"""Operational integrity overrides for multistore inventory workflows.

These endpoints replace the legacy purchase-receipt creation and physical-count
approval paths. They keep the existing behavior while closing two correctness
gaps:

* purchase receipts with the same invoice are serialized per location so two
  concurrent requests cannot both add the same stock;
* a physical count is rejected if stock/IMEI state changed after the count was
  captured, preventing a stale draft from overwriting legitimate movements.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import (
    IMEIHistory,
    Location,
    PhysicalInventoryCount,
    Product,
    ProductIMEI,
    PurchaseReceipt,
    PurchaseReceiptItem,
    StockHistory,
    Supplier,
    User,
)
from app.routers.multistore_control import (
    _serialize_count,
    _serialize_receipt,
    _stock_for_update,
)
from app.schemas import (
    InventoryCountApproveRequest,
    InventoryCountResponse,
    PurchaseReceiptCreate,
    PurchaseReceiptResponse,
)
from app.utils.audit import log_audit_event
from app.utils.location_access import require_location_access


router = APIRouter(prefix="/api/multistore-control", tags=["multistore-control"])


def _normalize_invoice_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _count_snapshot_is_stale(
    db: Session,
    *,
    count: PhysicalInventoryCount,
    product: Product,
    expected_quantity: int,
) -> bool:
    """Return True when inventory changed after the physical snapshot was taken.

    Product/Stock rows are already locked by the caller. History checks detect
    same-net-quantity churn as well as ordinary stock changes. The current-state
    comparisons are an additional guard for legacy/direct mutations that may not
    have emitted history records.
    """
    snapshot_at = count.counted_at or count.created_at

    stock = _stock_for_update(db, int(product.id), int(count.location_id))
    if int(stock.cantidad_disponible or 0) != int(expected_quantity or 0):
        return True

    stock_change = (
        db.query(StockHistory.id)
        .filter(
            StockHistory.product_id == product.id,
            StockHistory.location_id == count.location_id,
            StockHistory.created_at > snapshot_at,
        )
        .first()
    )
    if stock_change:
        return True

    if product.is_serialized:
        current_imei_count = (
            db.query(ProductIMEI.id)
            .filter(
                ProductIMEI.product_id == product.id,
                ProductIMEI.location_id == count.location_id,
                ProductIMEI.vendido == False,  # noqa: E712
                ProductIMEI.transfer_id == None,  # noqa: E711
            )
            .count()
        )
        if int(current_imei_count) != int(expected_quantity or 0):
            return True

        imei_change = (
            db.query(IMEIHistory.id)
            .filter(
                IMEIHistory.product_id == product.id,
                IMEIHistory.location_id == count.location_id,
                IMEIHistory.created_at > snapshot_at,
            )
            .first()
        )
        if imei_change:
            return True

    return False


@router.post(
    "/purchase-receipts",
    response_model=PurchaseReceiptResponse,
    dependencies=[Depends(check_permission("purchases:manage"))],
)
def create_purchase_receipt_integrity(
    payload: PurchaseReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("purchases:manage")),
):
    require_location_access(db, current_user, payload.location_id, "can_receive_purchase")

    # Serialize the duplicate-invoice check and receipt mutation per location.
    # Without this lock, two requests can both observe "no duplicate" before
    # either transaction commits and then both increase stock.
    location = (
        db.query(Location)
        .filter(Location.id == payload.location_id)
        .with_for_update()
        .first()
    )
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    if payload.supplier_id and not db.query(Supplier).filter(Supplier.id == payload.supplier_id).first():
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    invoice_number = _normalize_invoice_number(payload.invoice_number)
    if invoice_number:
        duplicate_query = db.query(PurchaseReceipt).filter(
            PurchaseReceipt.location_id == payload.location_id,
            func.upper(func.trim(PurchaseReceipt.invoice_number)) == invoice_number.upper(),
        )
        if payload.supplier_id:
            duplicate_query = duplicate_query.filter(PurchaseReceipt.supplier_id == payload.supplier_id)
        else:
            duplicate_query = duplicate_query.filter(PurchaseReceipt.supplier_id == None)  # noqa: E711
        if duplicate_query.first():
            raise HTTPException(
                status_code=409,
                detail="Ya existe una recepción con esa factura para esta ubicación y proveedor",
            )

    receipt = PurchaseReceipt(
        supplier_id=payload.supplier_id,
        location_id=payload.location_id,
        invoice_number=invoice_number,
        notes=payload.notes,
        received_by=current_user.username,
    )
    db.add(receipt)
    db.flush()

    total_cost = Decimal("0")
    try:
        products_by_id: dict[int, Product] = {}
        for product_id in sorted({item.product_id for item in payload.items}):
            product = (
                db.query(Product)
                .filter(Product.id == product_id)
                .with_for_update(key_share=True)
                .first()
            )
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado")
            products_by_id[product_id] = product

        for item in payload.items:
            product = products_by_id[item.product_id]
            imeis = item.imeis or []
            if product.is_serialized and len(imeis) != item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Producto {product.nombre} requiere {item.quantity} IMEI(s)",
                )

            stock = _stock_for_update(db, item.product_id, payload.location_id)
            previous_stock = stock.cantidad_disponible
            stock.cantidad_disponible += item.quantity

            db.add(
                PurchaseReceiptItem(
                    receipt_id=receipt.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    imeis_json=json.dumps(imeis) if imeis else None,
                    notes=item.notes,
                )
            )
            total_cost += item.unit_cost * item.quantity

            if item.unit_cost > 0:
                product.costo = item.unit_cost
                if payload.supplier_id:
                    product.supplier_id = payload.supplier_id

            for imei in imeis:
                existing_imei = db.query(ProductIMEI).filter(ProductIMEI.imei == imei).first()
                if existing_imei:
                    raise HTTPException(status_code=400, detail=f"IMEI duplicado: {imei}")
                db.add(
                    ProductIMEI(
                        product_id=item.product_id,
                        location_id=payload.location_id,
                        supplier_id=payload.supplier_id,
                        imei=imei,
                        acquisition_type="purchase_receipt",
                        received_notes=payload.notes,
                        received_by=current_user.username,
                    )
                )
                db.add(
                    IMEIHistory(
                        imei=imei,
                        product_id=item.product_id,
                        location_id=payload.location_id,
                        supplier_id=payload.supplier_id,
                        event_type="purchase_received",
                        reference_id=receipt.id,
                        reference_type="purchase_receipt",
                        notes=payload.notes,
                        created_by=current_user.username,
                    )
                )

            db.add(
                StockHistory(
                    product_id=item.product_id,
                    location_id=payload.location_id,
                    tipo_cambio="COMPRA_RECIBIDA",
                    cantidad=item.quantity,
                    stock_anterior=previous_stock,
                    stock_nuevo=stock.cantidad_disponible,
                    referencia_id=receipt.id,
                    referencia_tipo="purchase_receipt",
                    notas=payload.notes or f"Recepción de compra {invoice_number or ''}".strip(),
                    usuario=current_user.username,
                )
            )

        receipt.total_cost = total_cost
        audit_payload = payload.model_dump()
        audit_payload["invoice_number"] = invoice_number
        log_audit_event(
            db,
            action="purchase_receipt.create",
            entity_type="purchase_receipt",
            entity_id=receipt.id,
            location_id=payload.location_id,
            user=current_user,
            after_data=audit_payload,
        )
        db.commit()
        db.refresh(receipt)
        return _serialize_receipt(receipt)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto de integridad al recibir la compra") from exc
    except Exception:
        db.rollback()
        raise


@router.post(
    "/inventory-counts/{count_id}/approve",
    response_model=InventoryCountResponse,
    dependencies=[Depends(check_permission("inventory:adjust"))],
)
def approve_inventory_count_integrity(
    count_id: int,
    payload: InventoryCountApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:adjust")),
):
    count = (
        db.query(PhysicalInventoryCount)
        .filter(PhysicalInventoryCount.id == count_id)
        .with_for_update()
        .first()
    )
    if not count:
        raise HTTPException(status_code=404, detail="Conteo no encontrado")
    if count.status != "draft":
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar conteos en borrador")
    require_location_access(db, current_user, count.location_id, "can_edit")

    try:
        product_ids = sorted({int(item.product_id) for item in count.items})
        locked_products = (
            db.query(Product)
            .filter(Product.id.in_(product_ids))
            .order_by(Product.id.asc())
            .with_for_update(key_share=True)
            .all()
        )
        locked_products_by_id = {int(product.id): product for product in locked_products}

        # Validate every snapshot before mutating anything. A stale count must be
        # recaptured; applying its old absolute quantity would erase legitimate
        # sales, purchases or transfers that occurred after counting.
        stale_products: list[str] = []
        for item in count.items:
            product = locked_products_by_id.get(int(item.product_id))
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
            if _count_snapshot_is_stale(
                db,
                count=count,
                product=product,
                expected_quantity=int(item.expected_quantity or 0),
            ):
                stale_products.append(product.nombre or f"Producto #{product.id}")

        if stale_products:
            raise HTTPException(
                status_code=409,
                detail=(
                    "El inventario cambió después de realizar el conteo. "
                    "Debe crear un conteo nuevo antes de aprobarlo. Productos afectados: "
                    + ", ".join(stale_products[:10])
                ),
            )

        for item in count.items:
            product = locked_products_by_id[int(item.product_id)]
            stock = _stock_for_update(db, item.product_id, count.location_id)
            previous = stock.cantidad_disponible
            stock.cantidad_disponible = item.counted_quantity
            counted_imeis = set(json.loads(item.imeis_json) if item.imeis_json else [])

            if product.is_serialized:
                expected_imeis = (
                    db.query(ProductIMEI)
                    .filter(
                        ProductIMEI.product_id == item.product_id,
                        ProductIMEI.location_id == count.location_id,
                        ProductIMEI.vendido == False,  # noqa: E712
                        ProductIMEI.transfer_id == None,  # noqa: E711
                    )
                    .all()
                )
                for imei_record in expected_imeis:
                    if imei_record.imei not in counted_imeis:
                        imei_record.location_id = None
                        imei_record.acquisition_type = "conteo_fisico_faltante"
                        imei_record.received_notes = (
                            payload.notes or item.notes or "IMEI no encontrado en conteo físico"
                        )
                        db.add(
                            IMEIHistory(
                                imei=imei_record.imei,
                                product_id=imei_record.product_id,
                                location_id=count.location_id,
                                event_type="conteo_fisico_faltante",
                                reference_id=count.id,
                                reference_type="physical_inventory_count",
                                notes=payload.notes or item.notes or "IMEI no encontrado en conteo físico",
                                created_by=current_user.username,
                            )
                        )

            db.add(
                StockHistory(
                    product_id=item.product_id,
                    location_id=count.location_id,
                    tipo_cambio="CONTEO_FISICO",
                    cantidad=item.counted_quantity - previous,
                    stock_anterior=previous,
                    stock_nuevo=stock.cantidad_disponible,
                    referencia_id=count.id,
                    referencia_tipo="physical_inventory_count",
                    notas=payload.notes or item.notes or "Ajuste por conteo físico",
                    usuario=current_user.username,
                )
            )

        count.status = "approved"
        count.approved_by = current_user.username
        count.approved_at = datetime.now(UTC)
        log_audit_event(
            db,
            action="inventory_count.approve",
            entity_type="physical_inventory_count",
            entity_id=count.id,
            location_id=count.location_id,
            user=current_user,
            metadata={"notes": payload.notes},
        )
        db.commit()
        db.refresh(count)
        return _serialize_count(count)
    except Exception:
        db.rollback()
        raise
