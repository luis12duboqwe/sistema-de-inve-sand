from datetime import datetime, timezone

from app.models import Location, Order, OrderItem, Product, ProductIMEI, Stock, StockHistory, StockTransfer


def test_super_admin_can_purge_product_and_related_records(client, db_session):
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

    stock = Stock(product_id=product.id, location_id=location.id, cantidad_disponible=2, cantidad_reservada=1, cantidad_defectuosa=0)
    db_session.add(stock)

    imei = ProductIMEI(product_id=product.id, location_id=location.id, imei="356000000000000")
    db_session.add(imei)

    stock_history = StockHistory(
        product_id=product.id,
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

    order_item = OrderItem(order_id=order.id, product_id=product.id, cantidad=1, precio_unitario=500)
    db_session.add(order_item)

    transfer = StockTransfer(
        product_id=product.id,
        from_location_id=location.id,
        to_location_id=location.id,
        cantidad=1,
        estado="pendiente",
        created_by="test",
    )
    db_session.add(transfer)
    db_session.commit()

    response = client.post(
        f"/api/super-admin/products/{product.id}/purge",
        json={"reason": "Eliminación de prueba para purga total"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["deleted_counts"]["products"] == 1
    assert payload["deleted_counts"]["imeis"] == 1
    assert payload["deleted_counts"]["stock"] == 1

    db_session.expire_all()
    assert db_session.query(Product).filter(Product.id == product.id).count() == 0
    assert db_session.query(ProductIMEI).filter(ProductIMEI.product_id == product.id).count() == 0
    assert db_session.query(Stock).filter(Stock.product_id == product.id).count() == 0
    assert db_session.query(StockHistory).filter(StockHistory.product_id == product.id).count() == 0
    assert db_session.query(OrderItem).filter(OrderItem.product_id == product.id).count() == 0
    assert db_session.query(StockTransfer).filter(StockTransfer.product_id == product.id).count() == 0
