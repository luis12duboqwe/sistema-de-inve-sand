import pytest
from fastapi import HTTPException

from app.models import Location, User
from app.routers.locations import update_location
from app.schemas import LocationUpdate


def _actor() -> User:
    return User(
        username="location-admin",
        email="location-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _location(name: str) -> Location:
    return Location(nombre=name, tipo="tienda", activo=True)


def test_update_location_preserves_duplicate_name_as_400(db_session):
    first = _location("Tienda Centro")
    second = _location("Tienda Norte")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_location(
            second.id,
            LocationUpdate(nombre="  TIENDA CENTRO  "),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in exc_info.value.detail
    db_session.refresh(second)
    assert second.nombre == "Tienda Norte"


def test_update_location_preserves_blank_name_as_400(db_session):
    location = _location("Tienda Valida")
    db_session.add(location)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_location(
            location.id,
            LocationUpdate(nombre="   "),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "no puede estar vacío" in exc_info.value.detail
    db_session.refresh(location)
    assert location.nombre == "Tienda Valida"


def test_update_location_still_trims_and_persists_valid_name(db_session):
    location = _location("Tienda Inicial")
    db_session.add(location)
    db_session.commit()

    response = update_location(
        location.id,
        LocationUpdate(nombre="  Tienda Actualizada  "),
        db=db_session,
        current_user=_actor(),
    )

    assert response.nombre == "Tienda Actualizada"
    db_session.refresh(location)
    assert location.nombre == "Tienda Actualizada"
