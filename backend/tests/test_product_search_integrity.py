from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Product
from app.routers.product_search_integrity import MAX_PRODUCT_SEARCH_KEYWORDS


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


def test_product_search_limits_sql_keyword_expansion_to_six(
    client: TestClient,
    db_session: Session,
) -> None:
    first_six = "alphaone betatwo gammathree deltafour epsilonfive zetasix"
    _add_products(
        db_session,
        first_six,
        f"{first_six} needle-seven-only",
    )

    names = _search_names(client, f"{first_six} needle-seven-only")

    assert MAX_PRODUCT_SEARCH_KEYWORDS == 6
    assert first_six in names
    assert f"{first_six} needle-seven-only" in names


def test_product_list_exposes_canonical_get_route(client: TestClient) -> None:
    schema_response = client.get("/openapi.json")
    assert schema_response.status_code == 200, schema_response.text

    product_path = schema_response.json()["paths"]["/api/products"]
    assert "get" in product_path
    assert product_path["get"]["operationId"].startswith("list_products_integrity_")
