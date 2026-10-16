from app.models import (
    Location,
    Order,
    OrderItem,
    Product,
    ProductIMEI,
    Stock,
    StockHistory,
    StockTransfer,
)


def test_super_admin_rejects_purge_of_product_with_sale_history(client, db_session):
    location = Location(nombre="Tienda Test", tipo="tienda", activo=True)
    db_session.add(location)
    db_session.flush()

    product = Product(
        sku="PURGE-001",
        nombre="Celular de prueba",
        categoria="celular",
        marca="Marca",
        modelo="Modelo",
        condicion="Excelente",
        precio=500,
        activo=True,
        is_serialized=True,
    )
    db_session.add(product)
    db_session.flush()
    product_id = product.id

    stock = Stock(
        product_id=product_id,
        location_id=location.id,
        cantidad_disponible=2,
        cantidad_reservada=1,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)

    imei = ProductIMEI(
        product_id=product_id,
        location_id=location.id,
        imei="356000000000000",
    )
    db_session.add(imei)

    stock_history = StockHistory(
        product_id=product_id,
        location_id=location.id,
        tipo_cambio="compra",
        cantidad=2,
        stock_anterior=0,
        stock_nuevo=2,
        notas="historial de prueba",
        usuario="test",
    )
    db_session.add(stock_history)

    order = Order(
        customer_name="Cliente",
        customer_phone="99999999",
        canal="whatsapp",
        metodo_pago="efectivo",
        total=500,
        estado="pendiente",
    )
    db_session.add(order)
    db_session.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_id=product_id,
        cantidad=1,
        precio_unitario=500,
    )
    db_session.add(order_item)

    transfer = StockTransfer(
        product_id=product_id,
        from_location_id=location.id,
        to_location_id=location.id,
        cantidad=1,
        estado="pendiente",
        created_by="test",
    )
    db_session.add(transfer)
    db_session.commit()

    response = client.post(
        f"/api/super-admin/products/{product_id}/purge",
        json={"reason": "Eliminación de prueba para purga total"},
    )

    assert response.status_code == 409
    assert "históricas" in response.json()["detail"]

    db_session.expire_all()
    assert db_session.get(Product, product_id) is not None
    assert db_session.query(ProductIMEI).filter_by(product_id=product_id).count() == 1
    assert db_session.query(Stock).filter_by(product_id=product_id).count() == 1
    assert db_session.query(OrderItem).filter_by(product_id=product_id).count() == 1
    assert db_session.query(StockTransfer).filter_by(product_id=product_id).count() == 1



def test_super_admin_can_purge_unlinked_test_product(client, db_session):
    from uuid import uuid4
    suffix = uuid4().hex
    product = Product(sku=f"PURGE-SAFE-{suffix}", nombre="Producto descartable",
                      categoria="accesorio", marca="Test", modelo="Safe",
                      condicion="nuevo", precio=100, activo=True)
    db_session.add(product)
    db_session.commit()
    product_id = product.id
    response = client.post(
        f"/api/super-admin/products/{product_id}/purge",
        json={"reason": "Borrado de fixture descartable sin ventas vinculadas"},
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.get(Product, product_id) is None
