from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Product


def _add_products(db_session: Session, *names: str) -> None:
    products = []
    for index, name in enumerate(names, start=1):
        products.append(
            Product(
                sku=f"PUBLIC-SEARCH-{uuid4().hex}-{index}",
                nombre=name,
                categoria="accesorio",
                marca="MarcaNeutral",
                modelo=f"Modelo{index}",
                condicion="nuevo",
                precio=Decimal("100.00"),
                costo=Decimal("50.00"),
                activo=True,
                is_serialized=False,
            )
        )
    db_session.add_all(products)
    db_session.commit()


def _search_names(client: TestClient, search: str) -> list[str]:
    response = client.get("/api/public/catalog", params={"search": search})
    assert response.status_code == 200, response.text
    return [item["nombre"] for item in response.json()["items"]]


def test_public_catalog_search_treats_percent_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_products(db_session, "Accesorio 100% Original", "Accesorio 100X Original")

    assert _search_names(client, "%") == ["Accesorio 100% Original"]


def test_public_catalog_search_treats_underscore_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_products(db_session, "Cable_USB Público", "CableXUSB Público")

    assert _search_names(client, "_") == ["Cable_USB Público"]


def test_public_catalog_search_treats_backslash_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_products(db_session, "Ruta\\Pública", "RutaXPública")

    assert _search_names(client, "\\") == ["Ruta\\Pública"]
