from datetime import UTC, datetime
from decimal import Decimal

from app.models import (
    AuditLog,
    IMEIHistory,
    Location,
    Order,
    Permission,
    Product,
    ProductIMEI,
    PurchaseReceipt,
    Role,
    Stock,
    StockHistory,
    StockTransfer,
    Supplier,
    User,
    UserLocationAccess,
)
from app.routers.multistore_control import list_purchase_receipts
from app.routers.products import list_products


def _seed_location_product(db_session, *, initial_stock=0, serialized=False):
    location = Location(nombre="Tienda Test", tipo="tienda", activo=True)
    supplier = Supplier(nombre="Proveedor Test", activo=True)
    product = Product(
        sku="TEST-MULTI-001" if not serialized else "TEST-MULTI-IMEI-001",
        nombre="Producto Multitienda",
        categoria="celular" if serialized else "accesorio",
        marca="Marca",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("600.00"),
        moneda="HNL",
        garantia_meses=12,
        activo=True,
        is_serialized=serialized,
    )
    db_session.add_all([location, supplier, product])
    db_session.flush()
    db_session.add(Stock(product_id=product.id, location_id=location.id, cantidad_disponible=initial_stock))
    db_session.commit()
    return location, supplier, product


def _seed_system_role_user(db_session, *, role_name="Vendedor", username="seller"):
    permission = Permission(slug="inventory:view", description="Ver inventario", module="inventory")
    role = Role(name=role_name, description=f"Rol {role_name}", is_system_role=True)
    role.permissions = [permission]
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        role=role,
    )
    db_session.add_all([permission, role, user])
    db_session.commit()
    return user


def test_list_products_system_role_without_location_rows_keeps_inventory_visible(db_session):
    _location, _supplier, product = _seed_location_product(db_session, initial_stock=4)
    user = _seed_system_role_user(db_session)

    response = list_products(
        search=None,
        location_id=None,
        include_inactive=True,
        page=1,
        per_page=50,
        db=db_session,
        current_user=user,
    )

    assert response.total == 1
    assert response.items[0].id == product.id
    assert response.items[0].stock_disponible == 4


def test_list_products_with_explicit_location_access_includes_zero_stock_when_requested(db_session):
    location, _supplier, product = _seed_location_product(db_session, initial_stock=0)
    user = _seed_system_role_user(db_session, username="scoped-seller")
    db_session.add(UserLocationAccess(
        user_id=user.id,
        location_id=location.id,
        can_view=True,
    ))
    db_session.commit()

    response = list_products(
        search=None,
        location_id=None,
        include_inactive=True,
        page=1,
        per_page=50,
        db=db_session,
        current_user=user,
    )

    assert response.total == 1
    assert response.items[0].id == product.id
    assert response.items[0].stock_disponible == 0


def test_list_products_with_explicit_location_access_hides_blocked_locations(db_session):
    allowed_location, _supplier, allowed_product = _seed_location_product(db_session, initial_stock=2)
    blocked_location = Location(nombre="Tienda Sin Acceso", tipo="tienda", activo=True)
    blocked_product = Product(
        sku="TEST-MULTI-BLOCKED-001",
        nombre="Producto Bloqueado",
        categoria="accesorio",
        marca="Marca",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("600.00"),
        moneda="HNL",
        garantia_meses=12,
        activo=True,
    )
    user = _seed_system_role_user(db_session, username="location-scoped-seller")
    db_session.add_all([blocked_location, blocked_product])
    db_session.flush()
    db_session.add_all([
        Stock(product_id=blocked_product.id, location_id=blocked_location.id, cantidad_disponible=9),
        UserLocationAccess(user_id=user.id, location_id=allowed_location.id, can_view=True),
    ])
    db_session.commit()

    response = list_products(
        search=None,
        location_id=None,
        include_inactive=True,
        page=1,
        per_page=50,
        db=db_session,
        current_user=user,
    )

    assert response.total == 1
    assert [item.id for item in response.items] == [allowed_product.id]


def test_purchase_receipt_updates_stock_and_audit(client, db_session):
    location, supplier, product = _seed_location_product(db_session, initial_stock=2)

    response = client.post(
        "/api/multistore-control/purchase-receipts",
        json={
            "supplier_id": supplier.id,
            "location_id": location.id,
            "invoice_number": "FAC-001",
            "items": [{"product_id": product.id, "quantity": 3, "unit_cost": "700.00"}],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["location_id"] == location.id
    assert data["total_cost"] == "2100.00"

    stock = db_session.query(Stock).filter_by(product_id=product.id, location_id=location.id).first()
    assert stock.cantidad_disponible == 5

    audit = db_session.query(AuditLog).filter_by(action="purchase_receipt.create").first()
    assert audit is not None
    assert audit.location_id == location.id


def test_inventory_count_approval_adjusts_stock(client, db_session):
    location, _supplier, product = _seed_location_product(db_session, initial_stock=7)

    create_response = client.post(
        "/api/multistore-control/inventory-counts",
        json={
            "location_id": location.id,
            "notes": "Conteo semanal",
            "items": [{"product_id": product.id, "counted_quantity": 5}],
        },
    )

    assert create_response.status_code == 200, create_response.text
    count_id = create_response.json()["id"]

    approve_response = client.post(
        f"/api/multistore-control/inventory-counts/{count_id}/approve",
        json={"notes": "Aprobado por prueba"},
    )

    assert approve_response.status_code == 200, approve_response.text
    approved = approve_response.json()
    assert approved["status"] == "approved"
    assert approved["items"][0]["difference"] == -2

    stock = db_session.query(Stock).filter_by(product_id=product.id, location_id=location.id).first()
    assert stock.cantidad_disponible == 5


def test_inventory_count_approval_removes_missing_serialized_imei_from_location(client, db_session):
    location, _supplier, product = _seed_location_product(db_session, initial_stock=2, serialized=True)
    present_imei = "990000000000101"
    missing_imei = "990000000000102"
    db_session.add_all([
        ProductIMEI(product_id=product.id, location_id=location.id, imei=present_imei, vendido=False),
        ProductIMEI(product_id=product.id, location_id=location.id, imei=missing_imei, vendido=False),
    ])
    db_session.commit()

    create_response = client.post(
        "/api/multistore-control/inventory-counts",
        json={
            "location_id": location.id,
            "notes": "Conteo IMEI",
            "items": [{"product_id": product.id, "counted_quantity": 1, "imeis": [present_imei]}],
        },
    )

    assert create_response.status_code == 200, create_response.text
    count_id = create_response.json()["id"]

    approve_response = client.post(
        f"/api/multistore-control/inventory-counts/{count_id}/approve",
        json={"notes": "Falta una unidad"},
    )

    assert approve_response.status_code == 200, approve_response.text

    missing_record = db_session.query(ProductIMEI).filter_by(imei=missing_imei).first()
    assert missing_record.location_id is None
    assert missing_record.acquisition_type == "conteo_fisico_faltante"

    present_record = db_session.query(ProductIMEI).filter_by(imei=present_imei).first()
    assert present_record.location_id == location.id

    history = db_session.query(IMEIHistory).filter_by(
        imei=missing_imei,
        event_type="conteo_fisico_faltante",
    ).first()
    assert history is not None

    stock = db_session.query(Stock).filter_by(product_id=product.id, location_id=location.id).first()
    assert stock.cantidad_disponible == 1


def test_partial_transfer_confirmation_releases_missing_stock(client, db_session):
    source, _supplier, product = _seed_location_product(db_session, initial_stock=10)
    destination = Location(nombre="Tienda Destino", tipo="tienda", activo=True)
    db_session.add(destination)
    db_session.commit()

    create_response = client.post(
        "/api/stock-transfers",
        json={
            "product_id": product.id,
            "from_location_id": source.id,
            "to_location_id": destination.id,
            "cantidad": 5,
            "notas": "Reposicion semanal",
        },
    )
    assert create_response.status_code == 201, create_response.text
    transfer_id = create_response.json()["id"]

    source_stock = db_session.query(Stock).filter_by(product_id=product.id, location_id=source.id).first()
    assert source_stock.cantidad_disponible == 10
    assert source_stock.cantidad_reservada == 5

    confirm_response = client.post(
        f"/api/stock-transfers/{transfer_id}/confirm",
        json={
            "confirmed_by": "tester",
            "received_quantity": 3,
            "incident_notes": "Llegaron 3 de 5 unidades; 2 quedan pendientes de revision en origen.",
        },
    )
    assert confirm_response.status_code == 200, confirm_response.text
    data = confirm_response.json()
    assert data["estado"] == "confirmada"
    assert data["received_quantity"] == 3
    assert data["missing_quantity"] == 2

    db_session.refresh(source_stock)
    destination_stock = db_session.query(Stock).filter_by(product_id=product.id, location_id=destination.id).first()
    transfer = db_session.query(StockTransfer).filter_by(id=transfer_id).first()
    partial_history = db_session.query(StockHistory).filter_by(
        referencia_id=transfer_id,
        referencia_tipo="transfer_partial",
    ).first()

    assert source_stock.cantidad_disponible == 7
    assert source_stock.cantidad_reservada == 0
    assert destination_stock.cantidad_disponible == 3
    assert transfer.received_quantity == 3
    assert transfer.missing_quantity == 2
    assert partial_history is not None
    assert partial_history.cantidad == 2


def test_manual_stock_adjustment_audits_without_restock_scope_error(client, db_session):
    location, _supplier, product = _seed_location_product(db_session, initial_stock=4)

    response = client.put(
        f"/api/products/{product.id}/stock?location_id={location.id}",
        json={"cantidad_disponible": 9},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["stock_nuevo"] == 9

    stock = db_session.query(Stock).filter_by(product_id=product.id, location_id=location.id).first()
    assert stock.cantidad_disponible == 9

    audit = db_session.query(AuditLog).filter_by(action="stock.manual_adjust").first()
    assert audit is not None
    assert audit.location_id == location.id


def test_create_product_preserves_currency_and_cost(client, db_session):
    location = Location(nombre="Tienda Moneda", tipo="tienda", activo=True)
    db_session.add(location)
    db_session.commit()

    response = client.post(
        "/api/products",
        json={
            "sku": "USD-COST-001",
            "nombre": "Producto USD",
            "categoria": "accesorio",
            "marca": "Marca",
            "modelo": "Modelo",
            "condicion": "nuevo",
            "precio": "25.00",
            "costo": "10.50",
            "moneda": "USD",
            "garantia_meses": 6,
            "stock_inicial": 2,
            "initial_location_id": location.id,
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["moneda"] == "USD"
    assert data["costo"] == "10.50"

    product = db_session.query(Product).filter_by(sku="USD-COST-001").first()
    assert product is not None
    assert product.moneda == "USD"
    assert product.costo == Decimal("10.50")


def test_update_product_persists_cost(client, db_session):
    _location, _supplier, product = _seed_location_product(db_session, initial_stock=1)

    response = client.put(
        f"/api/products/{product.id}",
        json={"costo": "725.25"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["costo"] == "725.25"

    db_session.refresh(product)
    assert product.costo == Decimal("725.25")


def test_purchase_receipt_list_respects_location_access_without_filter(db_session):
    allowed_location, supplier, _product = _seed_location_product(db_session, initial_stock=0)
    blocked_location = Location(nombre="Tienda Bloqueada", tipo="tienda", activo=True)
    user = User(
        username="restricted",
        email="restricted@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
    )
    db_session.add_all([blocked_location, user])
    db_session.flush()
    db_session.add(UserLocationAccess(
        user_id=user.id,
        location_id=allowed_location.id,
        can_view=True,
    ))
    db_session.add_all([
        PurchaseReceipt(supplier_id=supplier.id, location_id=allowed_location.id, invoice_number="ALLOWED", total_cost=Decimal("10.00")),
        PurchaseReceipt(supplier_id=supplier.id, location_id=blocked_location.id, invoice_number="BLOCKED", total_cost=Decimal("20.00")),
    ])
    db_session.commit()

    receipts = list_purchase_receipts(limit=100, db=db_session, current_user=user)

    assert [receipt.invoice_number for receipt in receipts] == ["ALLOWED"]


def test_location_daily_close_reconciles_all_payment_methods(client, db_session):
    location, _supplier, _product = _seed_location_product(db_session, initial_stock=0)
    close_date = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    db_session.add_all([
        Order(source_location_id=location.id, customer_name="Cliente Efectivo", customer_phone="1", canal="tienda", metodo_pago="efectivo", total=Decimal("100.00"), estado="validada", created_at=close_date),
        Order(source_location_id=location.id, customer_name="Cliente Transfer", customer_phone="2", canal="tienda", metodo_pago="transferencia", total=Decimal("200.00"), estado="validada", created_at=close_date),
        Order(source_location_id=location.id, customer_name="Cliente Tarjeta", customer_phone="3", canal="tienda", metodo_pago="tarjeta", total=Decimal("300.00"), estado="completada", created_at=close_date),
        Order(source_location_id=location.id, customer_name="Cliente Fin", customer_phone="4", canal="tienda", metodo_pago="financiamiento", total=Decimal("400.00"), estado="validada", created_at=close_date),
        Order(source_location_id=location.id, customer_name="Pendiente", customer_phone="5", canal="tienda", metodo_pago="efectivo", total=Decimal("999.00"), estado="pendiente", created_at=close_date),
    ])
    db_session.commit()

    response = client.post(
        "/api/multistore-control/location-daily-closes",
        json={
            "location_id": location.id,
            "close_date": close_date.isoformat(),
            "cash_counted": "100.00",
            "transfer_total": "190.00",
            "card_total": "300.00",
            "financing_total": "400.00",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["cash_expected"] == "100.00"
    assert data["transfer_expected"] == "200.00"
    assert data["card_expected"] == "300.00"
    assert data["financing_expected"] == "400.00"
    assert data["difference"] == "-10.00"
