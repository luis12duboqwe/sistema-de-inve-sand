from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Supplier


def _add_suppliers(db_session: Session, *names: str) -> None:
    db_session.add_all([Supplier(nombre=name, activo=True) for name in names])
    db_session.commit()


def _search_names(client: TestClient, search: str) -> list[str]:
    response = client.get("/api/suppliers", params={"search": search})
    assert response.status_code == 200, response.text
    return [item["nombre"] for item in response.json()["items"]]


def test_supplier_search_treats_percent_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_suppliers(db_session, "Proveedor 100% Real", "Proveedor 100X Real")

    assert _search_names(client, "%") == ["Proveedor 100% Real"]


def test_supplier_search_treats_underscore_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_suppliers(db_session, "Proveedor_A", "ProveedorXA")

    assert _search_names(client, "_") == ["Proveedor_A"]


def test_supplier_search_treats_backslash_as_literal(
    client: TestClient,
    db_session: Session,
) -> None:
    _add_suppliers(db_session, "Ruta\\Central", "RutaXCentral")

    assert _search_names(client, "\\") == ["Ruta\\Central"]
