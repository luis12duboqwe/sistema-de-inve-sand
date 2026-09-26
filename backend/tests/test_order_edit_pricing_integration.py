from decimal import Decimal
import json

from app.models import OrderItem

from .helpers import seed_location_and_sales_profile, seed_product


def test_order_edit_preserves_old_discount_and_catalog_prices_added_quantity(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=3,
        is_serialized=False,
        categoria="accesorio",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente edición segura",
            "customer_phone": "74444444",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                    "precio_unitario": 970,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    # Simula un cliente viejo o manipulado: intenta convertir las dos unidades en
    # regalo y forzar precio L1. El esquema neutraliza esos campos y el endpoint
    # canónico conserva L970 solo en la unidad ya pactada; la unidad nueva va a catálogo.
    edited = client.put(
        f"/api/orders/{order_id}",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 2,
                    "precio_unitario": 1,
                    "costo_unitario": 1,
                    "es_regalo_promocion": True,
                }
            ]
        },
    )
    assert edited.status_code == 200, edited.text

    db_session.expire_all()
    rows = (
        db_session.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .order_by(OrderItem.precio_unitario.asc())
        .all()
    )
    assert len(rows) == 2
    assert [Decimal(str(row.precio_unitario)) for row in rows] == [
        Decimal("970.00"),
        Decimal("1000.00"),
    ]
    assert [int(row.cantidad) for row in rows] == [1, 1]
    assert all(not bool(row.es_regalo_promocion) for row in rows)

    payload = edited.json()
    assert Decimal(str(payload["total"])) == Decimal("1970.00")


def test_order_edit_added_usd_quantity_uses_hnl_catalog_and_historical_cost(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    sales_profile.configuracion = json.dumps({"exchange_rate": 24.5})
    db_session.commit()
    db_session.refresh(sales_profile)

    product = seed_product(
        client,
        location.id,
        stock_inicial=3,
        is_serialized=False,
        categoria="accesorio",
        precio=100,
        costo=60,
        moneda="USD",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente edición USD",
            "customer_phone": "75554444",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])
    assert Decimal(str(created.json()["total"])) == Decimal("2450.00")

    edited = client.put(
        f"/api/orders/{order_id}",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 2,
                    "precio_unitario": 1,
                    "costo_unitario": 1,
                    "es_regalo_promocion": True,
                }
            ]
        },
    )
    assert edited.status_code == 200, edited.text

    db_session.expire_all()
    rows = (
        db_session.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .order_by(OrderItem.id.asc())
        .all()
    )
    assert len(rows) == 2
    assert [Decimal(str(row.precio_unitario)) for row in rows] == [
        Decimal("2450.00"),
        Decimal("2450.00"),
    ]
    assert [Decimal(str(row.costo_unitario)) for row in rows] == [
        Decimal("1470.00"),
        Decimal("1470.00"),
    ]
    assert all(not bool(row.es_regalo_promocion) for row in rows)
    assert Decimal(str(edited.json()["total"])) == Decimal("4900.00")


def test_order_edit_cannot_leave_only_preserved_gifts(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    paid_product = seed_product(
        client,
        location.id,
        stock_inicial=2,
        is_serialized=False,
        categoria="accesorio",
        costo=500,
        precio=1000,
        sku="PAID-EDIT-001",
    )
    gift_product = seed_product(
        client,
        location.id,
        stock_inicial=2,
        is_serialized=False,
        categoria="accesorio",
        costo=100,
        precio=300,
        sku="GIFT-EDIT-001",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente edición regalo",
            "customer_phone": "76665555",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": paid_product["id"],
                    "cantidad": 1,
                    "precio_unitario": 1000,
                },
                {
                    "product_id": gift_product["id"],
                    "cantidad": 1,
                    "precio_unitario": 300,
                    "es_regalo_promocion": True,
                },
            ],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])
    assert Decimal(str(created.json()["total"])) == Decimal("1000.00")

    edited = client.put(
        f"/api/orders/{order_id}",
        json={
            "items": [
                {
                    "product_id": gift_product["id"],
                    "cantidad": 1,
                }
            ]
        },
    )
    assert edited.status_code == 400, edited.text
    assert "únicamente regalos/promociones" in edited.json()["detail"]

    db_session.expire_all()
    rows = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    assert len(rows) == 2
    assert any(not bool(row.es_regalo_promocion) for row in rows)
    assert any(bool(row.es_regalo_promocion) for row in rows)
