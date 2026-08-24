from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import IMEIHistory, Location, Product, ProductIMEI, User
from app.routers.imeis import admin_add_missing_imei, admin_correct_imei
from app.schemas import IMEIAdminCorrectRequest, IMEIAdminCreateRequest


def _actor() -> User:
    return User(
        username="imei-super-admin",
        email="imei-super-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _location(name: str = "Tienda IMEI", active: bool = True) -> Location:
    return Location(nombre=name, tipo="tienda", activo=active)


def _product(sku: str, serialized: bool = True) -> Product:
    return Product(
        sku=sku,
        nombre=f"Producto {sku}",
        categoria="celular",
        marca="Marca",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("10000.00"),
        costo=Decimal("7000.00"),
        moneda="Lps",
        garantia_meses=2,
        activo=True,
        is_serialized=serialized,
    )


def test_admin_add_missing_rejects_non_serialized_product(db_session):
    product = _product("IMEI-NON-SERIAL", serialized=False)
    location = _location()
    db_session.add_all([product, location])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        admin_add_missing_imei(
            IMEIAdminCreateRequest(
                product_id=product.id,
                location_id=location.id,
                imei="123456789012345",
                reason="Corrección de inventario",
            ),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "serializados" in exc_info.value.detail


def test_admin_add_missing_rejects_inactive_location(db_session):
    product = _product("IMEI-INACTIVE-LOC")
    location = _location(active=False)
    db_session.add_all([product, location])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        admin_add_missing_imei(
            IMEIAdminCreateRequest(
                product_id=product.id,
                location_id=location.id,
                imei="123456789012345",
                reason="Corrección de inventario",
            ),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 404
    assert "inactiva" in exc_info.value.detail


def test_admin_add_missing_creates_serial_and_audit_history(db_session):
    product = _product("IMEI-ADD-HISTORY")
    location = _location()
    db_session.add_all([product, location])
    db_session.commit()

    response = admin_add_missing_imei(
        IMEIAdminCreateRequest(
            product_id=product.id,
            location_id=location.id,
            imei="123456789012345",
            reason="Faltaba el IMEI físico",
        ),
        db=db_session,
        current_user=_actor(),
    )

    assert response.imei == "123456789012345"
    assert response.product_id == product.id
    assert response.location_id == location.id
    assert response.vendido is False
    assert response.acquisition_type == "admin_correction"

    history = db_session.query(IMEIHistory).filter(
        IMEIHistory.imei == "123456789012345",
        IMEIHistory.event_type == "admin_add_missing",
    ).one()
    assert history.product_id == product.id
    assert history.location_id == location.id
    assert history.created_by == "imei-super-admin"


def test_admin_correct_rejects_sold_imei(db_session):
    product = _product("IMEI-SOLD-LOCK")
    location = _location()
    db_session.add_all([product, location])
    db_session.flush()
    record = ProductIMEI(
        product_id=product.id,
        location_id=location.id,
        imei="123456789012345",
        vendido=True,
        acquisition_type="initial_stock",
    )
    db_session.add(record)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        admin_correct_imei(
            record.id,
            IMEIAdminCorrectRequest(
                new_imei="543210987654321",
                reason="Corrección de digitación",
            ),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "disponible" in exc_info.value.detail
    db_session.refresh(record)
    assert record.imei == "123456789012345"


def test_admin_correct_rejects_duplicate_target_and_preserves_original(db_session):
    product = _product("IMEI-DUP-CORRECT")
    location = _location()
    db_session.add_all([product, location])
    db_session.flush()
    original = ProductIMEI(
        product_id=product.id,
        location_id=location.id,
        imei="123456789012345",
        vendido=False,
        acquisition_type="initial_stock",
    )
    existing = ProductIMEI(
        product_id=product.id,
        location_id=location.id,
        imei="543210987654321",
        vendido=False,
        acquisition_type="initial_stock",
    )
    db_session.add_all([original, existing])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        admin_correct_imei(
            original.id,
            IMEIAdminCorrectRequest(
                new_imei="543210987654321",
                reason="Corrección de digitación",
            ),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya está registrado" in exc_info.value.detail
    db_session.refresh(original)
    assert original.imei == "123456789012345"


def test_admin_correct_creates_from_and_to_history_entries(db_session):
    product = _product("IMEI-CORRECT-HISTORY")
    location = _location()
    db_session.add_all([product, location])
    db_session.flush()
    record = ProductIMEI(
        product_id=product.id,
        location_id=location.id,
        imei="123456789012345",
        vendido=False,
        acquisition_type="initial_stock",
        received_notes="Recepción inicial",
    )
    db_session.add(record)
    db_session.commit()

    response = admin_correct_imei(
        record.id,
        IMEIAdminCorrectRequest(
            new_imei="543210987654321",
            reason="Se digitó mal en recepción",
        ),
        db=db_session,
        current_user=_actor(),
    )

    assert response.imei == "543210987654321"
    assert "123456789012345" in (response.received_notes or "")
    assert "543210987654321" in (response.received_notes or "")

    events = db_session.query(IMEIHistory).filter(
        IMEIHistory.reference_id == record.id,
        IMEIHistory.reference_type == "product_imei",
    ).order_by(IMEIHistory.event_type).all()
    assert [(event.event_type, event.imei) for event in events] == [
        ("admin_correct_from", "123456789012345"),
        ("admin_correct_to", "543210987654321"),
    ]
