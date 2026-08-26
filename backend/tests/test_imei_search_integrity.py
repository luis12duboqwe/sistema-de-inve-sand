from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Product, ProductIMEI


def _seed_imeis(db_session: Session) -> tuple[str, str, str]:
    suffix = uuid4().hex
    product = Product(
        sku=f"IMEI-SEARCH-{suffix}",
        nombre="Producto búsqueda IMEI",
        categoria="telefono",
        marca="Marca",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("500.00"),
        activo=True,
        is_serialized=True,
    )
    db_session.add(product)
    db_session.flush()

    first = "111111111111111"
    second = "222222222222222"
    backslash = "33333\\333333333"
    db_session.add_all(
        [
            ProductIMEI(product_id=product.id, imei=first, vendido=False),
            ProductIMEI(product_id=product.id, imei=second, vendido=False),
            ProductIMEI(product_id=product.id, imei=backslash, vendido=False),
        ]
    )
    db_session.commit()
    return first, second, backslash


def _search(client: TestClient, value: str) -> dict:
    response = client.get("/api/imeis", params={"search": value})
    assert response.status_code == 200, response.text
    return response.json()


def test_imei_search_treats_percent_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_imeis(db_session)

    payload = _search(client, "%")

    assert payload["total"] == 0
    assert payload["items"] == []


def test_imei_search_treats_underscore_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_imeis(db_session)

    payload = _search(client, "_")

    assert payload["total"] == 0
    assert payload["items"] == []


def test_imei_search_treats_backslash_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _, _, expected = _seed_imeis(db_session)

    payload = _search(client, "\\")

    assert payload["total"] == 1
    assert [item["imei"] for item in payload["items"]] == [expected]
