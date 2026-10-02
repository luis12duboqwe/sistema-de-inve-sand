from decimal import Decimal
import json

from app.models import OrderItem, Profile

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
            "items": [{"product_id": product["id"], "cantidad": 1, "precio_unitario": 970}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    edited = client.put(
        f"/api/orders/{order_id}",
        json={
            "items": [{
                "product_id": product["id"],
                "cantidad": 2,
                "precio_unitario": 1,
                "costo_unitario": 1,
                "es_regalo_promocion": True,
            }]
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
    assert [Decimal(str(row.precio_unitario)) for row in rows] == [Decimal("970.00"), Decimal("1000.00")]
    assert [int(row.cantidad) for row in rows] == [1, 1]
    assert all(not bool(row.es_regalo_promocion) for row in rows)
    assert Decimal(str(edited.json()["total"])) == Decimal("1970.00")


def test_order_edit_rejects_retained_price_when_current_cost_has_risen_above_it(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=2,
        is_serialized=False,
        categoria="accesorio",
        precio=1000,
        costo=700,
        sku="EDIT-COST-GUARD-001",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente costo actualizado",
            "customer_phone": "74445555",
            "metodo_pago": "efectivo",
            "items": [{"product_id": product["id"], "cantidad": 1, "precio_unitario": 980}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    # Simula una reposición/cambio de costo posterior a la venta original.
    db_product = db_session.get(__import__("app.models", fromlist=["Product"]).Product, product["id"])
    db_product.costo = Decimal("990.00")
    db_session.commit()

    edited = client.put(
        f"/api/orders/{order_id}",
        json={"items": [{"product_id": product["id"], "cantidad": 1}]},
    )
    assert edited.status_code == 403, edited.text
    assert "por debajo del costo actual" in edited.json()["detail"]

    db_session.expire_all()
    rows = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    assert len(rows) == 1
    assert Decimal(str(rows[0].precio_unitario)) == Decimal("980.00")
    assert Decimal(str(rows[0].costo_unitario)) == Decimal("700.00")


def test_order_edit_preserves_old_usd_cost_when_exchange_rate_changes(client, db_session):
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
            "items": [{"product_id": product["id"], "cantidad": 1}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])
    assert Decimal(str(created.json()["total"])) == Decimal("2450.00")
    assert Decimal(str(created.json()["items"][0]["costo_unitario"])) == Decimal("1470.00")

    sales_profile.configuracion = json.dumps({"exchange_rate": 26.0})
    db_session.commit()

    edited = client.put(
        f"/api/orders/{order_id}",
        json={
            "items": [{
                "product_id": product["id"],
                "cantidad": 2,
                "precio_unitario": 1,
                "costo_unitario": 1,
                "es_regalo_promocion": True,
            }]
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
    assert [Decimal(str(row.precio_unitario)) for row in rows] == [Decimal("2450.00"), Decimal("2600.00")]
    assert [Decimal(str(row.costo_unitario)) for row in rows] == [Decimal("1470.00"), Decimal("1560.00")]
    assert all(not bool(row.es_regalo_promocion) for row in rows)
    assert Decimal(str(edited.json()["total"])) == Decimal("5050.00")


def test_legacy_profile_exchange_rate_survives_creation_and_edit(client, db_session):
    location, _ = seed_location_and_sales_profile(db_session)
    legacy_profile = Profile(
        name="Perfil legacy USD",
        slug="legacy-usd-edit",
        active=True,
        settings=json.dumps({"exchangeRate": 24.25}),
    )
    db_session.add(legacy_profile)
    db_session.commit()
    db_session.refresh(legacy_profile)

    product = seed_product(
        client,
        location.id,
        stock_inicial=3,
        is_serialized=False,
        categoria="accesorio",
        precio=100,
        costo=60,
        moneda="USD",
        sku="LEGACY-USD-001",
    )

    created = client.post(
        "/api/orders",
        json={
            "profile_slug": legacy_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente legacy USD",
            "customer_phone": "78887777",
            "metodo_pago": "efectivo",
            "items": [{"product_id": product["id"], "cantidad": 1}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])
    assert Decimal(str(created.json()["total"])) == Decimal("2425.00")

    edited = client.put(
        f"/api/orders/{order_id}",
        json={"items": [{"product_id": product["id"], "cantidad": 2}]},
    )
    assert edited.status_code == 200, edited.text
    assert Decimal(str(edited.json()["total"])) == Decimal("4850.00")

    db_session.expire_all()
    rows = (
        db_session.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .order_by(OrderItem.id.asc())
        .all()
    )
    assert len(rows) == 2
    assert [Decimal(str(row.precio_unitario)) for row in rows] == [Decimal("2425.00"), Decimal("2425.00")]
    assert [Decimal(str(row.costo_unitario)) for row in rows] == [Decimal("1455.00"), Decimal("1455.00")]


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
                {"product_id": paid_product["id"], "cantidad": 1, "precio_unitario": 1000},
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
        json={"items": [{"product_id": gift_product["id"], "cantidad": 1}]},
    )
    assert edited.status_code == 400, edited.text
    assert "únicamente regalos/promociones" in edited.json()["detail"]

    db_session.expire_all()
    rows = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    assert len(rows) == 2
    assert any(not bool(row.es_regalo_promocion) for row in rows)
    assert any(bool(row.es_regalo_promocion) for row in rows)


def test_order_edit_rejects_new_product_when_current_catalog_is_below_cost(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    existing = seed_product(
        client, location.id, stock_inicial=2, is_serialized=False,
        categoria="accesorio", precio=1000, costo=700, sku="EDIT-BASE-001",
    )
    added = seed_product(
        client, location.id, stock_inicial=2, is_serialized=False,
        categoria="accesorio", precio=1000, costo=700, sku="EDIT-ADDED-COST-001",
    )
    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug, "source_location_id": location.id,
            "canal": "tienda", "customer_name": "Cliente agregado costo",
            "customer_phone": "74446666", "metodo_pago": "efectivo",
            "items": [{"product_id": existing["id"], "cantidad": 1}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    Product = __import__("app.models", fromlist=["Product"]).Product
    added_db = db_session.get(Product, added["id"])
    added_db.costo = Decimal("1100.00")
    db_session.commit()

    edited = client.put(
        f"/api/orders/{order_id}",
        json={"items": [
            {"product_id": existing["id"], "cantidad": 1},
            {"product_id": added["id"], "cantidad": 1},
        ]},
    )
    assert edited.status_code == 403, edited.text
    assert "por debajo del costo actual" in edited.json()["detail"]


def test_order_edit_normalizes_pre_fix_raw_usd_catalog_price(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    sales_profile.configuracion = json.dumps({"exchange_rate": 24.5})
    db_session.commit()
    product = seed_product(
        client, location.id, stock_inicial=2, is_serialized=False,
        categoria="accesorio", precio=100, costo=60, moneda="USD", sku="LEGACY-RAW-USD-001",
    )
    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug, "source_location_id": location.id,
            "canal": "tienda", "customer_name": "Cliente legacy USD",
            "customer_phone": "74447777", "metodo_pago": "efectivo",
            "items": [{"product_id": product["id"], "cantidad": 1}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    row = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).one()
    row.precio_unitario = Decimal("100.00")
    row.costo_unitario = Decimal("60.00")
    db_session.commit()

    edited = client.put(
        f"/api/orders/{order_id}",
        json={"items": [{"product_id": product["id"], "cantidad": 1}]},
    )
    assert edited.status_code == 200, edited.text
    assert Decimal(str(edited.json()["items"][0]["precio_unitario"])) == Decimal("2450.00")
