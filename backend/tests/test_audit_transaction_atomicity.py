"""Prove that stock/order mutations roll back when their audit trail fails.

Uses CI PostgreSQL fixture, never a real business database.
"""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models import Location, Order, Product, ProductIMEI, Stock, StockHistory
from app.routers import orders, products
from .helpers import seed_location_and_sales_profile, seed_product


def test_manual_adjustment_and_history_are_one_transaction(db_session, monkeypatch):
    tag = uuid4().hex[:10]
    location = Location(nombre=f"Tienda ajuste {tag}", tipo="tienda", activo=True)
    product = Product(
        sku=f"AUDIT-ADJUST-{tag}", nombre="Accesorio ajuste",
        categoria="accesorio", marca="QA", modelo="QA",
        condicion="nuevo", precio=Decimal("500"),
        costo=Decimal("300"), moneda="Lps",
        is_serialized=False, activo=True,
    )
    db_session.add_all([location, product])
    db_session.flush()
    row = Stock(
        location_id=location.id, product_id=product.id,
        cantidad_disponible=8, cantidad_reservada=2,
    )
    db_session.add(row)
    db_session.commit()

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("synthetic audit-storage failure")

    monkeypatch.setattr(products, "log_audit_event", fail_audit)
    before_history = db_session.query(StockHistory).filter_by(
        product_id=product.id, location_id=location.id,
    ).count()

    with pytest.raises(RuntimeError, match="audit-storage failure"):
        products.set_product_stock_at_location(
            product_id=product.id, location_id=location.id, cantidad=13,
            db=db_session,
            current_user=SimpleNamespace(id=99, username="audit", is_superuser=True, role=None),
        )

    db_session.expire_all()
    saved = db_session.query(Stock).filter_by(
        product_id=product.id, location_id=location.id,
    ).one()
    assert saved.cantidad_disponible == 8
    assert saved.cantidad_reservada == 2
    assert db_session.query(StockHistory).filter_by(
        product_id=product.id, location_id=location.id,
    ).count() == before_history


def test_failed_order_audit_does_not_commit_sale_or_sell_imei(client, db_session, monkeypatch):
    location, profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)
    before = db_session.query(Order).count()
    serial = db_session.query(ProductIMEI).filter_by(
        product_id=product["id"],
    ).one()

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("synthetic audit-storage failure")

    monkeypatch.setattr(orders, "log_audit_event", fail_audit)
    payload = {
        "sales_profile_slug": profile.slug,
        "source_location_id": location.id,
        "canal": "tienda",
        "customer_name": "Cliente error de auditoría",
        "customer_phone": "50495550011",
        "metodo_pago": "efectivo",
        "items": [{
            "product_id": product["id"], "cantidad": 1,
            "imeis": [serial.imei], "precio_unitario": 1000,
        }],
    }
    try:
        response = client.post("/api/orders", json=payload)
    except RuntimeError as error:
        assert "audit-storage failure" in str(error)
    else:
        assert response.status_code == 500, response.text

    db_session.expire_all()
    assert db_session.query(Order).count() == before
    assert db_session.query(ProductIMEI).filter_by(id=serial.id).one().vendido is False
    stock = db_session.query(Stock).filter_by(
        location_id=location.id, product_id=product["id"],
    ).one()
    assert stock.cantidad_disponible == 1
