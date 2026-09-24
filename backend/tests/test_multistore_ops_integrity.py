from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.models import Location, PhysicalInventoryCount, PhysicalInventoryCountItem, Product, PurchaseReceipt, Stock, StockHistory
from app.routers.multistore_ops_integrity import (
    approve_inventory_count_integrity,
    create_purchase_receipt_integrity,
)
from app.schemas import InventoryCountApproveRequest, PurchaseReceiptCreate
from app.schemas.control import PurchaseReceiptItemCreate


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="ops-integrity",
        is_active=True,
        is_superuser=True,
        role=None,
    )


def _product(suffix: str, *, serialized: bool = False) -> Product:
    return Product(
        sku=f"OPS-{suffix}",
        nombre=f"Producto Ops {suffix}",
        categoria="celular" if serialized else "accesorio",
        marca="Marca QA",
        modelo=f"Modelo-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("500.00"),
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=serialized,
    )


def test_inventory_count_rejects_stale_snapshot(db_session):
    suffix = uuid4().hex
    location = Location(nombre=f"Tienda stale {suffix}", tipo="tienda", activo=True)
    product = _product(suffix)
    db_session.add_all([location, product])
    db_session.flush()
    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=10,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)
    count = PhysicalInventoryCount(
        location_id=location.id,
        status="draft",
        counted_by="counter",
    )
    db_session.add(count)
    db_session.flush()
    db_session.add(
        PhysicalInventoryCountItem(
            count_id=count.id,
            product_id=product.id,
            expected_quantity=10,
            counted_quantity=12,
            difference=2,
        )
    )
    db_session.commit()
    db_session.refresh(count)

    # A legitimate movement occurs after the physical count was captured.
    stock.cantidad_disponible = 11
    db_session.add(
        StockHistory(
            product_id=product.id,
            location_id=location.id,
            tipo_cambio="compra",
            cantidad=1,
            stock_anterior=10,
            stock_nuevo=11,
            usuario="buyer",
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        approve_inventory_count_integrity(
            int(count.id),
            InventoryCountApproveRequest(notes="must not overwrite movement"),
            db_session,
            _user(),
        )

    assert exc_info.value.status_code == 409
    assert "inventario cambió" in str(exc_info.value.detail)

    db_session.expire_all()
    persisted_stock = db_session.get(Stock, stock.id)
    persisted_count = db_session.get(PhysicalInventoryCount, count.id)
    assert persisted_stock is not None
    assert persisted_stock.cantidad_disponible == 11
    assert persisted_count is not None
    assert persisted_count.status == "draft"


def test_inventory_count_approves_unchanged_snapshot(db_session):
    suffix = uuid4().hex
    location = Location(nombre=f"Tienda fresh {suffix}", tipo="tienda", activo=True)
    product = _product(suffix)
    db_session.add_all([location, product])
    db_session.flush()
    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=10,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)
    count = PhysicalInventoryCount(location_id=location.id, status="draft", counted_by="counter")
    db_session.add(count)
    db_session.flush()
    db_session.add(
        PhysicalInventoryCountItem(
            count_id=count.id,
            product_id=product.id,
            expected_quantity=10,
            counted_quantity=8,
            difference=-2,
        )
    )
    db_session.commit()

    result = approve_inventory_count_integrity(
        int(count.id),
        InventoryCountApproveRequest(notes="fresh count"),
        db_session,
        _user(),
    )

    assert result.status == "approved"
    db_session.expire_all()
    persisted_stock = db_session.get(Stock, stock.id)
    assert persisted_stock is not None
    assert persisted_stock.cantidad_disponible == 8

    history = (
        db_session.query(StockHistory)
        .filter(
            StockHistory.product_id == product.id,
            StockHistory.location_id == location.id,
            StockHistory.tipo_cambio == "CONTEO_FISICO",
        )
        .one()
    )
    assert history.cantidad == -2
    assert history.stock_anterior == 10
    assert history.stock_nuevo == 8


def test_purchase_receipt_normalizes_duplicate_invoice(db_session):
    suffix = uuid4().hex
    location = Location(nombre=f"Tienda invoice {suffix}", tipo="tienda", activo=True)
    product = _product(suffix)
    db_session.add_all([location, product])
    db_session.commit()

    first = PurchaseReceiptCreate(
        location_id=location.id,
        invoice_number="  inv-001  ",
        items=[PurchaseReceiptItemCreate(product_id=product.id, quantity=1, unit_cost=Decimal("500.00"))],
    )
    second = PurchaseReceiptCreate(
        location_id=location.id,
        invoice_number="INV-001",
        items=[PurchaseReceiptItemCreate(product_id=product.id, quantity=1, unit_cost=Decimal("500.00"))],
    )

    created = create_purchase_receipt_integrity(first, db_session, _user())
    assert created.invoice_number == "inv-001"

    with pytest.raises(HTTPException) as exc_info:
        create_purchase_receipt_integrity(second, db_session, _user())
    assert exc_info.value.status_code == 409

    db_session.expire_all()
    stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product.id, Stock.location_id == location.id)
        .one()
    )
    assert stock.cantidad_disponible == 1
    assert db_session.query(PurchaseReceipt).filter(PurchaseReceipt.location_id == location.id).count() == 1


def test_concurrent_duplicate_purchase_receipt_only_applies_once(db_session):
    suffix = uuid4().hex
    location = Location(nombre=f"Tienda concurrent invoice {suffix}", tipo="tienda", activo=True)
    product = _product(suffix)
    db_session.add_all([location, product])
    db_session.commit()
    location_id = int(location.id)
    product_id = int(product.id)

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    start = Barrier(2)

    def receive(invoice: str) -> int:
        session = SessionLocal()
        try:
            start.wait(timeout=10)
            payload = PurchaseReceiptCreate(
                location_id=location_id,
                invoice_number=invoice,
                items=[
                    PurchaseReceiptItemCreate(
                        product_id=product_id,
                        quantity=1,
                        unit_cost=Decimal("500.00"),
                    )
                ],
            )
            try:
                create_purchase_receipt_integrity(payload, session, _user())
                return 201
            except HTTPException as exc:
                session.rollback()
                return int(exc.status_code)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(receive, ["RACE-001", " race-001 "]))

    assert sorted(results) == [201, 409]
    db_session.expire_all()
    stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product_id, Stock.location_id == location_id)
        .one()
    )
    assert stock.cantidad_disponible == 1
    assert db_session.query(PurchaseReceipt).filter(PurchaseReceipt.location_id == location_id).count() == 1
