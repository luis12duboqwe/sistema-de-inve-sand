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
                sku=f"SEARCH-{uuid4().hex}-{index}",
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
    response = client.get("/api/products", params={"search": search})
    assert response.status_code == 200, response.text
    return [item["nombre"] for item in response.json()["items"]]


def test_product_search_treats_percent_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_products(db_session, "Batería 100% Original", "Batería 100X Original")

    assert _search_names(client, "%") == ["Batería 100% Original"]


def test_product_search_treats_underscore_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_products(db_session, "Cable_USB", "CableXUSB")

    assert _search_names(client, "_") == ["Cable_USB"]


def test_product_search_treats_backslash_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_products(db_session, "Ruta\\Central", "RutaXCentral")

    assert _search_names(client, "\\") == ["Ruta\\Central"]


def test_product_list_exposes_single_canonical_get_route(client: TestClient) -> None:
    matching = [
        route
        for route in client.app.routes
        if getattr(route, "path", None) == "/api/products"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]

    assert len(matching) == 1
    assert matching[0].endpoint.__module__.endswith("product_search_integrity")
