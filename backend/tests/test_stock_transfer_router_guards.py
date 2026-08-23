import pytest
from fastapi import HTTPException

from app.models import Location, Product, Stock, StockTransfer, User
from app.routers.stock_transfer_integrity import (
    cancel_transfer_integrity,
    confirm_transfer_integrity,
    reject_transfer_integrity,
)
from app.routers.stock_transfers import get_transfer, list_transfers
from app.schemas import StockTransferConfirm, StockTransferReject


def _superuser() -> User:
    return User(
        username="transfer-admin",
        email="transfer-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _seed_pending_transfer(db_session, *, quantity: int = 5, reserved: int = 5):
    product = Product(
        sku="TRANSFER-TEST-001",
        nombre="Producto Transferencia",
        categoria="Telefonía",
        marca="Test",
        modelo="T1",
        condicion="nuevo",
        precio=100,
        costo=50,
        activo=True,
        is_serialized=False,
    )
    origin = Location(nombre="Tienda Origen", tipo="tienda", activo=True)
    destination = Location(nombre="Tienda Destino", tipo="tienda", activo=True)
    db_session.add_all([product, origin, destination])
    db_session.flush()

    stock = Stock(
        product_id=product.id,
        location_id=origin.id,
        cantidad_disponible=10,
        cantidad_reservada=reserved,
        cantidad_defectuosa=0,
    )
    transfer = StockTransfer(
        product_id=product.id,
        from_location_id=origin.id,
        to_location_id=destination.id,
        cantidad=quantity,
        estado="pendiente",
        created_by="transfer-admin",
    )
    db_session.add_all([stock, transfer])
    db_session.commit()
    db_session.refresh(transfer)
    return product, origin, destination, stock, transfer


def test_list_transfers_rejects_unknown_state(db_session):
    with pytest.raises(HTTPException) as exc_info:
        list_transfers(
            location_id=None,
            from_location_id=None,
            to_location_id=None,
            product_id=None,
            estado="desconocida",
            page=1,
            per_page=50,
            db=db_session,
            current_user=_superuser(),
        )

    assert exc_info.value.status_code == 400
    assert "Estado de transferencia inválido" in exc_info.value.detail


def test_transfer_lookup_and_canonical_state_actions_return_404_for_missing_transfer(db_session):
    actor = _superuser()

    with pytest.raises(HTTPException) as get_exc:
        get_transfer(999999, db=db_session, current_user=actor)
    assert get_exc.value.status_code == 404

    with pytest.raises(HTTPException) as confirm_exc:
        confirm_transfer_integrity(999999, StockTransferConfirm(), db=db_session, current_user=actor)
    assert confirm_exc.value.status_code == 404

    with pytest.raises(HTTPException) as reject_exc:
        reject_transfer_integrity(
            999999,
            StockTransferReject(rejection_reason="Transferencia inexistente"),
            db=db_session,
            current_user=actor,
        )
    assert reject_exc.value.status_code == 404

    with pytest.raises(HTTPException) as cancel_exc:
        cancel_transfer_integrity(999999, db=db_session, current_user=actor)
    assert cancel_exc.value.status_code == 404


def test_canonical_confirm_rejects_non_pending_state(db_session):
    _, _, _, _, transfer = _seed_pending_transfer(db_session)
    transfer.estado = "confirmada"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        confirm_transfer_integrity(
            transfer.id,
            StockTransferConfirm(),
            db=db_session,
            current_user=_superuser(),
        )

    assert exc_info.value.status_code == 400
    assert "Solo se puede operar una transferencia pendiente" in exc_info.value.detail


def test_canonical_reject_refuses_non_pending_state(db_session):
    _, _, _, _, transfer = _seed_pending_transfer(db_session)
    transfer.estado = "cancelada"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        reject_transfer_integrity(
            transfer.id,
            StockTransferReject(rejection_reason="Ya no aplica"),
            db=db_session,
            current_user=_superuser(),
        )

    assert exc_info.value.status_code == 400
    assert "Solo se puede operar una transferencia pendiente" in exc_info.value.detail


def test_canonical_cancel_refuses_non_pending_state(db_session):
    _, _, _, _, transfer = _seed_pending_transfer(db_session)
    transfer.estado = "rechazada"
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        cancel_transfer_integrity(transfer.id, db=db_session, current_user=_superuser())

    assert exc_info.value.status_code == 400
    assert "Solo se puede operar una transferencia pendiente" in exc_info.value.detail


def test_canonical_confirm_rejects_received_quantity_above_transfer(db_session):
    _, _, _, _, transfer = _seed_pending_transfer(db_session, quantity=5, reserved=5)

    with pytest.raises(HTTPException) as exc_info:
        confirm_transfer_integrity(
            transfer.id,
            StockTransferConfirm(received_quantity=6, incident_notes="Conteo de recepción"),
            db=db_session,
            current_user=_superuser(),
        )

    assert exc_info.value.status_code == 400
    assert "cantidad recibida debe estar entre 0 y la cantidad transferida" in exc_info.value.detail


def test_canonical_partial_reception_requires_incident_notes(db_session):
    _, _, _, _, transfer = _seed_pending_transfer(db_session, quantity=5, reserved=5)

    with pytest.raises(HTTPException) as exc_info:
        confirm_transfer_integrity(
            transfer.id,
            StockTransferConfirm(received_quantity=4),
            db=db_session,
            current_user=_superuser(),
        )

    assert exc_info.value.status_code == 400
    assert "notas de incidencia" in exc_info.value.detail


def test_canonical_confirm_fails_closed_when_reserved_stock_is_incomplete(db_session):
    _, _, _, _, transfer = _seed_pending_transfer(db_session, quantity=5, reserved=4)

    with pytest.raises(HTTPException) as exc_info:
        confirm_transfer_integrity(
            transfer.id,
            StockTransferConfirm(received_quantity=5),
            db=db_session,
            current_user=_superuser(),
        )

    assert exc_info.value.status_code == 409
    assert "Stock no reservado correctamente" in exc_info.value.detail
