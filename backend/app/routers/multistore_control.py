import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import (
    AuditLog,
    IMEIHistory,
    Location,
    LocationDailyClose,
    Order,
    PhysicalInventoryCount,
    PhysicalInventoryCountItem,
    Product,
    ProductIMEI,
    PurchaseReceipt,
    PurchaseReceiptItem,
    Stock,
    StockHistory,
    Supplier,
    User,
    UserLocationAccess,
)
from app.schemas import (
    AuditLogResponse,
    InventoryCountApproveRequest,
    InventoryCountCreate,
    InventoryCountResponse,
    LocationDailyCloseCreate,
    LocationDailyCloseResponse,
    PurchaseReceiptCreate,
    PurchaseReceiptResponse,
    UserLocationAccessResponse,
    UserLocationAccessUpsert,
)
from app.utils.audit import log_audit_event
from app.utils.location_access import get_accessible_location_ids, require_location_access

router = APIRouter(prefix="/api/multistore-control", tags=["multistore-control"])


def _loads(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {"raw": raw}


def _loads_list(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        return None
    return None


def _stock_for_update(db: Session, product_id: int, location_id: int) -> Stock:
    stock = db.query(Stock).filter(
        Stock.product_id == product_id,
        Stock.location_id == location_id,
    ).with_for_update().first()
    if stock:
        return stock

    stock = Stock(product_id=product_id, location_id=location_id, cantidad_disponible=0)
    db.add(stock)
    db.flush()
    return stock


def _serialize_access(row: UserLocationAccess) -> UserLocationAccessResponse:
    return UserLocationAccessResponse.model_validate(row)


def _serialize_receipt(receipt: PurchaseReceipt) -> PurchaseReceiptResponse:
    return PurchaseReceiptResponse(
        id=receipt.id,
        supplier_id=receipt.supplier_id,
        location_id=receipt.location_id,
        invoice_number=receipt.invoice_number,
        status=receipt.status,
        total_cost=receipt.total_cost,
        notes=receipt.notes,
        received_by=receipt.received_by,
        received_at=receipt.received_at,
        created_at=receipt.created_at,
        items=[
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
                    "imeis": _loads_list(item.imeis_json) or [],
                "notes": item.notes,
            }
            for item in receipt.items
        ],
    )


def _serialize_count(count: PhysicalInventoryCount) -> InventoryCountResponse:
    return InventoryCountResponse(
        id=count.id,
        location_id=count.location_id,
        status=count.status,
        notes=count.notes,
        counted_by=count.counted_by,
        approved_by=count.approved_by,
        counted_at=count.counted_at,
        approved_at=count.approved_at,
        created_at=count.created_at,
        items=[
            {
                "id": item.id,
                "product_id": item.product_id,
                "expected_quantity": item.expected_quantity,
                "counted_quantity": item.counted_quantity,
                "difference": item.difference,
                "imeis": _loads_list(item.imeis_json) or [],
                "notes": item.notes,
            }
            for item in count.items
        ],
    )


def _serialize_audit(row: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=row.id,
        user_id=row.user_id,
        username=row.username,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        location_id=row.location_id,
        before_data=_loads(row.before_data),
        after_data=_loads(row.after_data),
        metadata=_loads(row.metadata_json),
        created_at=row.created_at,
    )


def _payment_expected_total(db: Session, location_id: int, payment_method: str, day_start: datetime, day_end: datetime) -> Decimal:
    orders = db.query(Order).filter(
        Order.source_location_id == location_id,
        Order.estado.in_(["completada", "validada"]),
        Order.created_at >= day_start,
        Order.created_at <= day_end,
    ).all()

    total = Decimal("0")
    for order in orders:
        if getattr(order, "payment_breakdown", None):
            try:
                breakdown = json.loads(order.payment_breakdown)
            except (TypeError, json.JSONDecodeError):
                breakdown = []
            for item in breakdown:
                if isinstance(item, dict) and item.get("method") == payment_method:
                    total += Decimal(str(item.get("amount") or 0))
            continue

        if order.metodo_pago == payment_method:
            total += Decimal(str(order.total or 0))

    return total


@router.get("/location-access/me", response_model=List[UserLocationAccessResponse])
def get_my_location_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    rows = db.query(UserLocationAccess).filter(UserLocationAccess.user_id == current_user.id).all()
    return [_serialize_access(row) for row in rows]


@router.get("/location-access/users/{user_id}", response_model=List[UserLocationAccessResponse])
def list_user_location_access(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("locations:access_manage")),
):
    rows = db.query(UserLocationAccess).filter(UserLocationAccess.user_id == user_id).all()
    return [_serialize_access(row) for row in rows]


@router.put("/location-access/users/{user_id}", response_model=List[UserLocationAccessResponse])
def replace_user_location_access(
    user_id: int,
    payload: List[UserLocationAccessUpsert],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("locations:access_manage")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.query(UserLocationAccess).filter(UserLocationAccess.user_id == user_id).delete()
    rows: list[UserLocationAccess] = []
    for item in payload:
        if not db.query(Location).filter(Location.id == item.location_id).first():
            raise HTTPException(status_code=404, detail=f"Ubicación {item.location_id} no encontrada")
        row = UserLocationAccess(user_id=user_id, **item.model_dump())
        db.add(row)
        rows.append(row)

    log_audit_event(
        db,
        action="location_access.replace",
        entity_type="user",
        entity_id=user_id,
        user=current_user,
        after_data=[item.model_dump() for item in payload],
    )
    db.commit()
    for row in rows:
        db.refresh(row)
    return [_serialize_access(row) for row in rows]


@router.post("/purchase-receipts", response_model=PurchaseReceiptResponse, dependencies=[Depends(check_permission("purchases:manage"))])
def create_purchase_receipt(
    payload: PurchaseReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("purchases:manage")),
):
    require_location_access(db, current_user, payload.location_id, "can_receive_purchase")
    if not db.query(Location).filter(Location.id == payload.location_id).first():
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    if payload.supplier_id and not db.query(Supplier).filter(Supplier.id == payload.supplier_id).first():
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if payload.invoice_number:
        duplicate_query = db.query(PurchaseReceipt).filter(
            PurchaseReceipt.location_id == payload.location_id,
            PurchaseReceipt.invoice_number == payload.invoice_number,
        )
        if payload.supplier_id:
            duplicate_query = duplicate_query.filter(PurchaseReceipt.supplier_id == payload.supplier_id)
        else:
            duplicate_query = duplicate_query.filter(PurchaseReceipt.supplier_id == None)
        if duplicate_query.first():
            raise HTTPException(status_code=409, detail="Ya existe una recepción con esa factura para esta ubicación y proveedor")

    receipt = PurchaseReceipt(
        supplier_id=payload.supplier_id,
        location_id=payload.location_id,
        invoice_number=payload.invoice_number,
        notes=payload.notes,
        received_by=current_user.username,
    )
    db.add(receipt)
    db.flush()

    total_cost = Decimal("0")
    try:
        for item in payload.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
            imeis = item.imeis or []
            if product.is_serialized and len(imeis) != item.quantity:
                raise HTTPException(status_code=400, detail=f"Producto {product.nombre} requiere {item.quantity} IMEI(s)")

            stock = _stock_for_update(db, item.product_id, payload.location_id)
            previous_stock = stock.cantidad_disponible
            stock.cantidad_disponible += item.quantity

            receipt_item = PurchaseReceiptItem(
                receipt_id=receipt.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                imeis_json=json.dumps(imeis) if imeis else None,
                notes=item.notes,
            )
            db.add(receipt_item)
            total_cost += item.unit_cost * item.quantity

            if item.unit_cost > 0:
                product.costo = item.unit_cost
                if payload.supplier_id:
                    product.supplier_id = payload.supplier_id

            for imei in imeis:
                existing_imei = db.query(ProductIMEI).filter(ProductIMEI.imei == imei).first()
                if existing_imei:
                    raise HTTPException(status_code=400, detail=f"IMEI duplicado: {imei}")
                db.add(ProductIMEI(
                    product_id=item.product_id,
                    location_id=payload.location_id,
                    supplier_id=payload.supplier_id,
                    imei=imei,
                    acquisition_type="purchase_receipt",
                    received_notes=payload.notes,
                    received_by=current_user.username,
                ))
                db.add(IMEIHistory(
                    imei=imei,
                    product_id=item.product_id,
                    location_id=payload.location_id,
                    supplier_id=payload.supplier_id,
                    event_type="purchase_received",
                    reference_id=receipt.id,
                    reference_type="purchase_receipt",
                    notes=payload.notes,
                    created_by=current_user.username,
                ))

            db.add(StockHistory(
                product_id=item.product_id,
                location_id=payload.location_id,
                tipo_cambio="COMPRA_RECIBIDA",
                cantidad=item.quantity,
                stock_anterior=previous_stock,
                stock_nuevo=stock.cantidad_disponible,
                referencia_id=receipt.id,
                referencia_tipo="purchase_receipt",
                notas=payload.notes or f"Recepción de compra {payload.invoice_number or ''}".strip(),
                usuario=current_user.username,
            ))

        receipt.total_cost = total_cost
        log_audit_event(db, action="purchase_receipt.create", entity_type="purchase_receipt", entity_id=receipt.id, location_id=payload.location_id, user=current_user, after_data=payload.model_dump())
        db.commit()
        db.refresh(receipt)
        return _serialize_receipt(receipt)
    except Exception:
        db.rollback()
        raise


@router.get("/purchase-receipts", response_model=List[PurchaseReceiptResponse])
def list_purchase_receipts(
    location_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    query = db.query(PurchaseReceipt)
    if location_id:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(PurchaseReceipt.location_id == location_id)
    else:
        accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
        if accessible_location_ids is not None:
            if not accessible_location_ids:
                return []
            query = query.filter(PurchaseReceipt.location_id.in_(accessible_location_ids))
    if supplier_id:
        query = query.filter(PurchaseReceipt.supplier_id == supplier_id)
    receipts = query.order_by(PurchaseReceipt.received_at.desc()).limit(limit).all()
    return [_serialize_receipt(receipt) for receipt in receipts]


@router.post("/inventory-counts", response_model=InventoryCountResponse, dependencies=[Depends(check_permission("inventory:count"))])
def create_inventory_count(
    payload: InventoryCountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:count")),
):
    require_location_access(db, current_user, payload.location_id, "can_count_stock")
    if not db.query(Location).filter(Location.id == payload.location_id).first():
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    count = PhysicalInventoryCount(location_id=payload.location_id, notes=payload.notes, counted_by=current_user.username)
    db.add(count)
    db.flush()

    try:
        for item in payload.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
            stock = db.query(Stock).filter(Stock.product_id == item.product_id, Stock.location_id == payload.location_id).first()
            imeis = [imei.strip() for imei in (item.imeis or []) if imei.strip()]

            if product.is_serialized:
                if len(set(imeis)) != len(imeis):
                    raise HTTPException(status_code=400, detail=f"Hay IMEIs duplicados en el conteo de {product.nombre}")
                if item.counted_quantity != len(imeis):
                    raise HTTPException(status_code=400, detail=f"La cantidad contada de {product.nombre} debe coincidir con los IMEIs escaneados")
                expected_records = db.query(ProductIMEI).filter(
                    ProductIMEI.product_id == item.product_id,
                    ProductIMEI.location_id == payload.location_id,
                    ProductIMEI.vendido == False,
                    ProductIMEI.transfer_id == None,
                ).all()
                expected = len(expected_records)
                records = db.query(ProductIMEI).filter(
                    ProductIMEI.product_id == item.product_id,
                    ProductIMEI.location_id == payload.location_id,
                    ProductIMEI.vendido == False,
                    ProductIMEI.transfer_id == None,
                    ProductIMEI.imei.in_(imeis),
                ).all() if imeis else []
                found = {record.imei for record in records}
                missing = sorted(set(imeis) - found)
                if missing:
                    raise HTTPException(status_code=400, detail=f"IMEIs no disponibles para {product.nombre}: {', '.join(missing)}")
            else:
                expected = stock.cantidad_disponible if stock else 0

            db.add(PhysicalInventoryCountItem(
                count_id=count.id,
                product_id=item.product_id,
                expected_quantity=expected,
                counted_quantity=item.counted_quantity,
                difference=item.counted_quantity - expected,
                imeis_json=json.dumps(imeis) if imeis else None,
                notes=item.notes,
            ))

        log_audit_event(db, action="inventory_count.create", entity_type="physical_inventory_count", entity_id=count.id, location_id=payload.location_id, user=current_user, after_data=payload.model_dump())
        db.commit()
        db.refresh(count)
        return _serialize_count(count)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto de integridad al crear el conteo físico. Verifique datos duplicados")
    except Exception:
        db.rollback()
        raise


@router.get("/inventory-counts", response_model=List[InventoryCountResponse])
def list_inventory_counts(
    location_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    query = db.query(PhysicalInventoryCount)
    if location_id:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(PhysicalInventoryCount.location_id == location_id)
    else:
        accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
        if accessible_location_ids is not None:
            if not accessible_location_ids:
                return []
            query = query.filter(PhysicalInventoryCount.location_id.in_(accessible_location_ids))
    if status:
        query = query.filter(PhysicalInventoryCount.status == status)
    counts = query.order_by(PhysicalInventoryCount.counted_at.desc()).limit(limit).all()
    return [_serialize_count(count) for count in counts]


@router.post("/inventory-counts/{count_id}/approve", response_model=InventoryCountResponse, dependencies=[Depends(check_permission("inventory:adjust"))])
def approve_inventory_count(
    count_id: int,
    payload: InventoryCountApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:adjust")),
):
    count = db.query(PhysicalInventoryCount).filter(PhysicalInventoryCount.id == count_id).first()
    if not count:
        raise HTTPException(status_code=404, detail="Conteo no encontrado")
    if count.status != "draft":
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar conteos en borrador")
    require_location_access(db, current_user, count.location_id, "can_edit")

    try:
        for item in count.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            stock = _stock_for_update(db, item.product_id, count.location_id)
            previous = stock.cantidad_disponible
            stock.cantidad_disponible = item.counted_quantity
            counted_imeis = set(_loads_list(item.imeis_json) or [])
            if product and product.is_serialized:
                expected_imeis = db.query(ProductIMEI).filter(
                    ProductIMEI.product_id == item.product_id,
                    ProductIMEI.location_id == count.location_id,
                    ProductIMEI.vendido == False,
                    ProductIMEI.transfer_id == None,
                ).all()
                for imei_record in expected_imeis:
                    if imei_record.imei not in counted_imeis:
                        imei_record.location_id = None
                        imei_record.acquisition_type = "conteo_fisico_faltante"
                        imei_record.received_notes = payload.notes or item.notes or "IMEI no encontrado en conteo físico"
                        db.add(IMEIHistory(
                            imei=imei_record.imei,
                            product_id=imei_record.product_id,
                            location_id=count.location_id,
                            event_type="conteo_fisico_faltante",
                            reference_id=count.id,
                            reference_type="physical_inventory_count",
                            notes=payload.notes or item.notes or "IMEI no encontrado en conteo físico",
                            created_by=current_user.username,
                        ))
            db.add(StockHistory(
                product_id=item.product_id,
                location_id=count.location_id,
                tipo_cambio="CONTEO_FISICO",
                cantidad=item.difference,
                stock_anterior=previous,
                stock_nuevo=stock.cantidad_disponible,
                referencia_id=count.id,
                referencia_tipo="physical_inventory_count",
                notas=payload.notes or item.notes or "Ajuste por conteo físico",
                usuario=current_user.username,
            ))

        count.status = "approved"
        count.approved_by = current_user.username
        count.approved_at = datetime.now(UTC)
        log_audit_event(db, action="inventory_count.approve", entity_type="physical_inventory_count", entity_id=count.id, location_id=count.location_id, user=current_user, metadata={"notes": payload.notes})
        db.commit()
        db.refresh(count)
        return _serialize_count(count)
    except Exception:
        db.rollback()
        raise


@router.post("/location-daily-closes", response_model=LocationDailyCloseResponse, dependencies=[Depends(check_permission("cash_closes:manage"))])
def create_location_daily_close(
    payload: LocationDailyCloseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("cash_closes:manage")),
):
    require_location_access(db, current_user, payload.location_id, "can_close_cash")
    if not db.query(Location).filter(Location.id == payload.location_id).first():
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")

    close_day = payload.close_date.date()
    day_start = payload.close_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = payload.close_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    existing_close = db.query(LocationDailyClose).filter(
        LocationDailyClose.location_id == payload.location_id,
        LocationDailyClose.close_day == close_day,
    ).first()
    if existing_close:
        raise HTTPException(status_code=409, detail="Ya existe un cierre de caja para esta ubicación en esa fecha")

    cash_expected = _payment_expected_total(db, payload.location_id, "efectivo", day_start, day_end)
    transfer_expected = _payment_expected_total(db, payload.location_id, "transferencia", day_start, day_end)
    card_expected = _payment_expected_total(db, payload.location_id, "tarjeta", day_start, day_end)
    financing_expected = _payment_expected_total(db, payload.location_id, "financiamiento", day_start, day_end)
    expected_total = cash_expected + transfer_expected + card_expected + financing_expected
    counted_total = payload.cash_counted + payload.transfer_total + payload.card_total + payload.financing_total

    close = LocationDailyClose(
        location_id=payload.location_id,
        close_date=payload.close_date,
        close_day=close_day,
        cash_expected=cash_expected,
        transfer_expected=transfer_expected,
        card_expected=card_expected,
        financing_expected=financing_expected,
        cash_counted=payload.cash_counted,
        transfer_total=payload.transfer_total,
        card_total=payload.card_total,
        financing_total=payload.financing_total,
        difference=counted_total - expected_total,
        notes=payload.notes,
        closed_by=current_user.username,
    )
    try:
        db.add(close)
        db.flush()
        log_audit_event(db, action="location_daily_close.create", entity_type="location_daily_close", entity_id=close.id, location_id=payload.location_id, user=current_user, after_data=payload.model_dump())
        db.commit()
        db.refresh(close)
        return LocationDailyCloseResponse.model_validate(close)
    except Exception:
        db.rollback()
        raise


@router.get("/location-daily-closes", response_model=List[LocationDailyCloseResponse])
def list_location_daily_closes(
    location_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    query = db.query(LocationDailyClose)
    if location_id:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(LocationDailyClose.location_id == location_id)
    else:
        accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
        if accessible_location_ids is not None:
            if not accessible_location_ids:
                return []
            query = query.filter(LocationDailyClose.location_id.in_(accessible_location_ids))
    closes = query.order_by(LocationDailyClose.close_date.desc()).limit(limit).all()
    return [LocationDailyCloseResponse.model_validate(close) for close in closes]


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    location_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("audit:view")),
):
    query = db.query(AuditLog)
    if location_id:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(AuditLog.location_id == location_id)
    else:
        accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
        if accessible_location_ids is not None:
            if not accessible_location_ids:
                return []
            query = query.filter((AuditLog.location_id.is_(None)) | (AuditLog.location_id.in_(accessible_location_ids)))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [_serialize_audit(row) for row in rows]