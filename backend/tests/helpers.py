import json


def seed_location_and_sales_profile(db):
    from app.models import Location, SalesProfile

    location = Location(nombre="Tienda Test", tipo="tienda", direccion="", telefono=None, activo=True)
    db.add(location)

    sales_profile = SalesProfile(
        name="Bot Test",
        slug="bot-whatsapp",
        tipo="bot_ia",
        canales=json.dumps(["whatsapp"]),
        active=True,
        configuracion=None,
    )
    db.add(sales_profile)
    db.commit()
    db.refresh(location)
    db.refresh(sales_profile)
    return location, sales_profile


def seed_product(client, location_id: int):
    payload = {
        "sku": "TEST-DEVICE-001",
        "nombre": "Telefono Test",
        "categoria": "celular",
        "marca": "MarcaX",
        "modelo": "ModeloY",
        "condicion": "nuevo",
        "precio": 1000,
        "costo": 500,
        "moneda": "Lps",
        "garantia_meses": 12,
        "stock_inicial": 1,
        "initial_location_id": location_id,
        "is_serialized": True,
        "imeis_con_ubicacion": [{"imei": "111111111111111", "location_id": location_id}],
    }
    response = client.post("/api/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
