from datetime import UTC, datetime
from decimal import Decimal

from app.auth import get_current_active_user, get_current_user, get_current_user_optional
from app.main import app
from app.models import Location, Order, OrderItem, Product, ProductIMEI, Return, ReturnItem, SalesProfile, Stock, User, UserLocationAccess


class _Permission:
    def __init__(self, slug: str):
        self.slug = slug


class _Role:
    permissions = [
        _Permission("inventory:view"),
        _Permission("orders:view"),
        _Permission("reports:view"),
        _Permission("settings:view"),
    ]


class _RestrictedUser:
    id = 77
    username = "tienda-uno"
    email = "tienda-uno@example.com"
    is_active = True
    is_superuser = False
    role = _Role()


def _restricted_user():
    return _RestrictedUser()


class _InventoryWriteRole:
    permissions = [
        _Permission("inventory:create"),
        _Permission("inventory:edit"),
        _Permission("inventory:view"),
        _Permission("orders:view"),
    ]


class _RestrictedInventoryWriter(_RestrictedUser):
    role = _InventoryWriteRole()


def _restricted_inventory_writer():
    return _RestrictedInventoryWriter()


class _SuperUser:
    id = 1
    username = "admin"
    email = "admin@example.com"
    is_active = True
    is_superuser = True
    role = _Role()


def _super_user():
    return _SuperUser()


def _seed_two_store_data(db_session):
    location_one = Location(nombre="Tienda Uno", tipo="tienda", activo=True)
    location_two = Location(nombre="Tienda Dos", tipo="tienda", activo=True)
    sales_profile = SalesProfile(
        name="Vendedor Test",
        slug="vendedor-test",
        tipo="vendedor_humano",
        canales='["tienda"]',
        active=True,
    )
    db_session.add_all([location_one, location_two, sales_profile])
    db_session.commit()

    product_one = Product(
        sku="LOC-ONE",
        nombre="Producto Tienda Uno",
        categoria="accesorio",
        marca="Marca",
        modelo="Uno",
        condicion="nuevo",
        precio=Decimal("100.00"),
        costo=Decimal("50.00"),
        is_serialized=False,
    )
    product_two = Product(
        sku="LOC-TWO",
        nombre="Producto Tienda Dos",
        categoria="accesorio",
        marca="Marca",
        modelo="Dos",
        condicion="nuevo",
        precio=Decimal("200.00"),
        costo=Decimal("80.00"),
        is_serialized=False,
    )
    db_session.add_all([product_one, product_two])
    db_session.commit()

    db_session.add_all([
        User(
            id=77,
            username="tienda-uno",
            email="tienda-uno@example.com",
            hashed_password="test",
            is_active=True,
            is_superuser=False,
        ),
        Stock(product_id=product_one.id, location_id=location_one.id, cantidad_disponible=3),
        Stock(product_id=product_two.id, location_id=location_two.id, cantidad_disponible=5),
        UserLocationAccess(user_id=77, location_id=location_one.id, can_view=True),
    ])
    db_session.commit()

    order_one = Order(
        sales_profile_id=sales_profile.id,
        source_location_id=location_one.id,
        customer_name="Cliente Uno",
        customer_phone="1111",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("100.00"),
        estado="completada",
    )
    order_two = Order(
        sales_profile_id=sales_profile.id,
        source_location_id=location_two.id,
        customer_name="Cliente Dos",
        customer_phone="2222",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("200.00"),
        estado="completada",
    )
    pending_order = Order(
        sales_profile_id=sales_profile.id,
        source_location_id=location_one.id,
        customer_name="Cliente Uno",
        customer_phone="1111",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("999.00"),
        estado="pendiente",
    )
    db_session.add_all([order_one, order_two, pending_order])
    db_session.commit()

    db_session.add_all([
        OrderItem(order_id=order_one.id, product_id=product_one.id, cantidad=1, precio_unitario=Decimal("100.00")),
        OrderItem(order_id=order_two.id, product_id=product_two.id, cantidad=1, precio_unitario=Decimal("200.00")),
    ])
    db_session.commit()
    return location_one, location_two


def test_restricted_user_only_reads_accessible_location_data(client, db_session):
    location_one, location_two = _seed_two_store_data(db_session)

    app.dependency_overrides[get_current_user] = _restricted_user
    app.dependency_overrides[get_current_user_optional] = _restricted_user
    app.dependency_overrides[get_current_active_user] = _restricted_user

    products = client.get("/api/products?per_page=50")
    assert products.status_code == 200, products.text
    product_names = {item["nombre"] for item in products.json()["items"]}
    assert "Producto Tienda Uno" in product_names
    assert "Producto Tienda Dos" not in product_names

    orders = client.get("/api/orders?per_page=50")
    assert orders.status_code == 200, orders.text
    customer_names = {item["customer_name"] for item in orders.json()["items"]}
    assert customer_names == {"Cliente Uno"}

    locations = client.get("/api/locations")
    assert locations.status_code == 200, locations.text
    assert [item["id"] for item in locations.json()] == [location_one.id]

    forbidden_stock = client.get(f"/api/locations/{location_two.id}/stock")
    assert forbidden_stock.status_code == 403

    summary = client.get("/api/reports/sales-summary-by-location")
    assert summary.status_code == 200, summary.text
    assert [item["location_id"] for item in summary.json()] == [location_one.id]

    alerts = client.get("/api/reports/inventory/alerts")
    assert alerts.status_code == 200, alerts.text
    assert {item["product_name"] for item in alerts.json()} == {"Producto Tienda Uno"}

    dashboard = client.get("/api/reports/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    dashboard_data = dashboard.json()
    assert dashboard_data["active_products"] == 1
    assert dashboard_data["total_products"] == 1
    assert dashboard_data["total_inventory_value"] == 150
    assert dashboard_data["total_revenue_today"] == 100

    analytics_dashboard = client.get("/api/analytics/dashboard")
    assert analytics_dashboard.status_code == 200, analytics_dashboard.text
    analytics_data = analytics_dashboard.json()
    assert analytics_data["active_products"] == 1
    assert analytics_data["total_products"] == 1
    assert analytics_data["total_inventory_value"] == 150
    assert analytics_data["total_revenue_today"] == 100

    forecast = client.post("/api/analytics/forecast", json={"days_history": 60, "limit": 10, "use_cache": False})
    assert forecast.status_code == 200, forecast.text
    forecast_names = {item["product_name"] for item in forecast.json()["forecasts"]}
    assert forecast_names == {"Marca Uno"}

    insights = client.post("/api/ai/business-insights", json={"days": 30, "use_cache": False})
    assert insights.status_code == 200, insights.text
    insights_data = insights.json()
    assert Decimal(str(insights_data["metrics"]["kpis"]["total_revenue"])) == Decimal("100.0")
    assert {item["product_name"] for item in insights_data["metrics"]["top_sellers"]} == {"Producto Tienda Uno"}

    sales = client.get("/api/reports/sales")
    assert sales.status_code == 200, sales.text
    sales_data = sales.json()
    assert sales_data["total_orders"] == 1
    assert Decimal(str(sales_data["total_revenue"])) == Decimal("100.00")

    daily_close_pending = client.get("/api/daily-close/pending")
    assert daily_close_pending.status_code == 200, daily_close_pending.text
    assert [item["customer_name"] for item in daily_close_pending.json()] == ["Cliente Uno"]

    customers = client.get("/api/customers")
    assert customers.status_code == 200, customers.text
    assert customers.json()[0]["customer_name"] == "Cliente Uno"
    assert Decimal(str(customers.json()[0]["total_spent"])) == Decimal("100.00")


def test_location_daily_close_rejects_duplicate_day(client, db_session):
    location = Location(nombre="Tienda Cierre", tipo="tienda", activo=True)
    db_session.add(location)
    db_session.commit()

    close_date = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    payload = {
        "location_id": location.id,
        "close_date": close_date.isoformat(),
        "cash_counted": "0.00",
        "transfer_total": "0.00",
        "card_total": "0.00",
        "financing_total": "0.00",
    }

    first = client.post("/api/multistore-control/location-daily-closes", json=payload)
    assert first.status_code == 200, first.text

    duplicate = client.post("/api/multistore-control/location-daily-closes", json=payload)
    assert duplicate.status_code == 409, duplicate.text


def test_business_insights_cache_is_scoped_by_location_access(client, db_session):
    _seed_two_store_data(db_session)
    app.state.business_insights_cache = {}

    app.dependency_overrides[get_current_user] = _super_user
    app.dependency_overrides[get_current_user_optional] = _super_user
    app.dependency_overrides[get_current_active_user] = _super_user

    global_insights = client.post("/api/ai/business-insights", json={"days": 30, "use_cache": True})
    assert global_insights.status_code == 200, global_insights.text
    assert global_insights.headers["X-AI-Business-Cache"] == "MISS"
    assert Decimal(str(global_insights.json()["metrics"]["kpis"]["total_revenue"])) == Decimal("300.0")

    app.dependency_overrides[get_current_user] = _restricted_user
    app.dependency_overrides[get_current_user_optional] = _restricted_user
    app.dependency_overrides[get_current_active_user] = _restricted_user

    scoped_insights = client.post("/api/ai/business-insights", json={"days": 30, "use_cache": True})
    assert scoped_insights.status_code == 200, scoped_insights.text
    assert scoped_insights.headers["X-AI-Business-Cache"] == "MISS"
    scoped_data = scoped_insights.json()
    assert Decimal(str(scoped_data["metrics"]["kpis"]["total_revenue"])) == Decimal("100.0")
    assert {item["product_name"] for item in scoped_data["metrics"]["top_sellers"]} == {"Producto Tienda Uno"}


def test_restricted_user_cannot_access_blocked_order_by_id(client, db_session):
    _location_one, location_two = _seed_two_store_data(db_session)
    blocked_order = db_session.query(Order).filter(Order.source_location_id == location_two.id).first()

    app.dependency_overrides[get_current_user] = _restricted_user
    app.dependency_overrides[get_current_user_optional] = _restricted_user
    app.dependency_overrides[get_current_active_user] = _restricted_user

    detail = client.get(f"/api/orders/{blocked_order.id}")
    assert detail.status_code == 403

    cancel = client.post(f"/api/orders/{blocked_order.id}/cancel?reason=test")
    assert cancel.status_code == 403

    delete = client.delete(f"/api/orders/{blocked_order.id}")
    assert delete.status_code == 403


def test_restricted_user_only_reads_accessible_returns(client, db_session):
    location_one, location_two = _seed_two_store_data(db_session)
    order_one = db_session.query(Order).filter(Order.source_location_id == location_one.id).first()
    order_two = db_session.query(Order).filter(Order.source_location_id == location_two.id).first()
    product_one = db_session.query(Product).filter(Product.sku == "LOC-ONE").first()
    product_two = db_session.query(Product).filter(Product.sku == "LOC-TWO").first()

    return_one = Return(order_id=order_one.id, reason="visible", status="completed", created_by="test")
    return_two = Return(order_id=order_two.id, reason="blocked", status="completed", created_by="test")
    db_session.add_all([return_one, return_two])
    db_session.flush()
    db_session.add_all([
        ReturnItem(return_id=return_one.id, product_id=product_one.id, quantity=1, condition="nuevo", action="refund"),
        ReturnItem(return_id=return_two.id, product_id=product_two.id, quantity=1, condition="nuevo", action="refund"),
    ])
    db_session.commit()

    app.dependency_overrides[get_current_user] = _restricted_user
    app.dependency_overrides[get_current_user_optional] = _restricted_user
    app.dependency_overrides[get_current_active_user] = _restricted_user

    response = client.get("/api/returns")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["reason"] == "visible"


def test_restricted_user_cannot_read_blocked_product_and_imeis(client, db_session):
    _location_one, location_two = _seed_two_store_data(db_session)
    blocked_product = db_session.query(Product).filter(Product.sku == "LOC-TWO").first()
    db_session.add(ProductIMEI(
        product_id=blocked_product.id,
        location_id=location_two.id,
        imei="990000000000002",
        vendido=False,
    ))
    db_session.commit()

    app.dependency_overrides[get_current_user] = _restricted_user
    app.dependency_overrides[get_current_user_optional] = _restricted_user
    app.dependency_overrides[get_current_active_user] = _restricted_user

    product_detail = client.get(f"/api/products/{blocked_product.id}")
    assert product_detail.status_code == 404

    imeis = client.get(f"/api/products/{blocked_product.id}/imeis")
    assert imeis.status_code == 200, imeis.text
    assert imeis.json() == []

    imei_detail = client.get("/api/imeis/detail/990000000000002")
    assert imei_detail.status_code == 403

    imei_list = client.get("/api/imeis")
    assert imei_list.status_code == 200, imei_list.text
    assert imei_list.json()["total"] == 0


def test_restricted_inventory_writer_cannot_mutate_blocked_location_stock(client, db_session):
    _location_one, location_two = _seed_two_store_data(db_session)
    blocked_product = db_session.query(Product).filter(Product.sku == "LOC-TWO").first()

    app.dependency_overrides[get_current_user] = _restricted_inventory_writer
    app.dependency_overrides[get_current_user_optional] = _restricted_inventory_writer
    app.dependency_overrides[get_current_active_user] = _restricted_inventory_writer

    create_response = client.post(
        "/api/products",
        json={
            "sku": "BLOCKED-STOCK-CREATE",
            "nombre": "Producto Bloqueado",
            "categoria": "accesorio",
            "marca": "Marca",
            "modelo": "Bloqueado",
            "condicion": "nuevo",
            "precio": "100.00",
            "costo": "50.00",
            "stock_inicial": 1,
            "initial_location_id": location_two.id,
        },
    )
    assert create_response.status_code == 403, create_response.text

    adjust_response = client.post(
        f"/api/products/{blocked_product.id}/stock/location/{location_two.id}?cantidad=9"
    )
    assert adjust_response.status_code == 403, adjust_response.text


def test_restricted_ai_user_cannot_create_order_in_blocked_location(client, db_session):
    _location_one, location_two = _seed_two_store_data(db_session)
    blocked_product = db_session.query(Product).filter(Product.sku == "LOC-TWO").first()

    app.dependency_overrides[get_current_user] = _restricted_inventory_writer
    app.dependency_overrides[get_current_user_optional] = _restricted_inventory_writer
    app.dependency_overrides[get_current_active_user] = _restricted_inventory_writer

    response = client.post(
        "/api/ai/create-order",
        json={
            "sales_profile_slug": "vendedor-test",
            "source_location_id": location_two.id,
            "customer_phone": "50470001111",
            "customer_name": "Cliente Bloqueado",
            "items": [{"product_id": blocked_product.id, "cantidad": 1}],
        },
    )

    assert response.status_code == 403, response.text
