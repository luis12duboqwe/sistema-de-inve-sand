from uuid import uuid4

from app.models import Location, Product, Stock, StockTransfer


def test_transfer_idempotency_does_not_double_reserve(client, db_session):
    tag = uuid4().hex[:10]
    source = Location(nombre=f"Tr Origen {tag}", tipo="tienda", activo=True)
    target = Location(nombre=f"Tr Destino {tag}", tipo="tienda", activo=True)
    product = Product(
        sku=f"TR-RETRY-{tag}", nombre="Accesorio reintento",
        categoria="accesorio", marca="Test", modelo=tag,
        condicion="nuevo", precio=200, activo=True, is_serialized=False,
    )
    db_session.add_all([source, target, product])
    db_session.flush()
    db_session.add(Stock(product_id=product.id, location_id=source.id,
                         cantidad_disponible=5, cantidad_reservada=0))
    db_session.commit()

    payload = {
        "product_id": product.id,
        "from_location_id": source.id,
        "to_location_id": target.id,
        "cantidad": 2,
    }
    headers = {"Idempotency-Key": f"transfer-{tag}-safe"}
    first = client.post("/api/stock-transfers", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    replay = client.post("/api/stock-transfers", json=payload, headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    db_session.expire_all()
    stock = db_session.query(Stock).filter_by(
        product_id=product.id, location_id=source.id,
    ).one()
    assert stock.cantidad_reservada == 2
    assert db_session.query(StockTransfer).filter_by(product_id=product.id).count() == 1

    conflict = client.post("/api/stock-transfers",
                           json={**payload, "cantidad": 3}, headers=headers)
    assert conflict.status_code == 409, conflict.text
