import json
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - hints for tests only
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

    from app.models import Location, SalesProfile


def seed_location_and_sales_profile(db: "Session") -> Tuple["Location", "SalesProfile"]:
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


def seed_product(
    client: "TestClient",
    location_id: int,
    *,
    stock_inicial: int = 1,
    imei_values: Optional[List[str]] = None,
    is_serialized: bool = True,
) -> dict[str, Any]:
    """Crea un producto de prueba permitiendo ajustar stock e IMEIs."""

    if is_serialized:
        imei_list = imei_values or ["111111111111111"]
        imeis_con_ubicacion = [
            {"imei": str(imei), "location_id": location_id}
            for imei in imei_list
        ]
        stock_value = len(imei_list)
    else:
        imeis_con_ubicacion = []
        stock_value = stock_inicial

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
        "stock_inicial": stock_value,
        "initial_location_id": location_id,
        "is_serialized": is_serialized,
        "imeis_con_ubicacion": imeis_con_ubicacion,
    }

    response = client.post("/api/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
