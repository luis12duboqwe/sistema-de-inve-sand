import pytest
from fastapi import HTTPException

from app.models import Supplier, User
from app.routers.suppliers import update_supplier
from app.schemas import SupplierUpdate


def _actor() -> User:
    return User(
        username="supplier-admin",
        email="supplier-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _supplier(name: str) -> Supplier:
    return Supplier(nombre=name, activo=True)


def test_update_supplier_preserves_duplicate_name_as_400(db_session):
    first = _supplier("Proveedor Uno")
    second = _supplier("Proveedor Dos")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_supplier(
            second.id,
            SupplierUpdate(nombre="  PROVEEDOR UNO  "),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in exc_info.value.detail
    db_session.refresh(second)
    assert second.nombre == "Proveedor Dos"


def test_update_supplier_preserves_blank_name_as_400(db_session):
    supplier = _supplier("Proveedor Valido")
    db_session.add(supplier)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_supplier(
            supplier.id,
            SupplierUpdate(nombre="   "),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "no puede estar vacío" in exc_info.value.detail
    db_session.refresh(supplier)
    assert supplier.nombre == "Proveedor Valido"


def test_update_supplier_still_trims_and_persists_valid_name(db_session):
    supplier = _supplier("Proveedor Inicial")
    db_session.add(supplier)
    db_session.commit()

    response = update_supplier(
        supplier.id,
        SupplierUpdate(nombre="  Proveedor Actualizado  "),
        db=db_session,
        current_user=_actor(),
    )

    assert response.nombre == "Proveedor Actualizado"
    db_session.refresh(supplier)
    assert supplier.nombre == "Proveedor Actualizado"
