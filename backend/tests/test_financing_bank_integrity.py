import pytest
from fastapi import HTTPException

from app.models import Bank, User
from app.routers.financing import create_bank, update_bank
from app.schemas import BankCreate, BankUpdate


def _actor() -> User:
    return User(
        username="finance-admin",
        email="finance-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _bank(name: str) -> Bank:
    return Bank(name=name, active=True, normal_card_rate=0)


def test_update_bank_rejects_duplicate_name_as_400(db_session):
    first = _bank("Banco Uno")
    second = _bank("Banco Dos")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_bank(
            second.id,
            BankUpdate(name="Banco Uno"),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in exc_info.value.detail
    db_session.refresh(second)
    assert second.name == "Banco Dos"


def test_create_bank_rejects_existing_name_as_400(db_session):
    db_session.add(_bank("Banco Existente"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name="Banco Existente", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_create_bank_rejects_case_insensitive_trimmed_duplicate(db_session):
    db_session.add(_bank("Banco Uno"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name="  banco uno  ", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in exc_info.value.detail
    assert db_session.query(Bank).count() == 1


def test_update_bank_rejects_case_insensitive_trimmed_duplicate(db_session):
    first = _bank("Banco Uno")
    second = _bank("Banco Dos")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_bank(
            second.id,
            BankUpdate(name="  BANCO UNO  "),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    db_session.refresh(second)
    assert second.name == "Banco Dos"


def test_bank_name_matching_tolerates_legacy_outer_whitespace(db_session):
    db_session.add(_bank("  Banco Legacy  "))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name="banco legacy", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert db_session.query(Bank).count() == 1


def test_create_and_update_reject_blank_normalized_names(db_session):
    bank = _bank("Banco Inicial")
    db_session.add(bank)
    db_session.commit()

    with pytest.raises(HTTPException) as create_exc:
        create_bank(
            BankCreate(name="  ", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )
    with pytest.raises(HTTPException) as update_exc:
        update_bank(
            bank.id,
            BankUpdate(name="  "),
            db=db_session,
            current_user=_actor(),
        )

    assert create_exc.value.status_code == 400
    assert update_exc.value.status_code == 400
    db_session.refresh(bank)
    assert bank.name == "Banco Inicial"


def test_create_bank_stores_trimmed_name(db_session):
    response = create_bank(
        BankCreate(name="  Banco Nuevo  ", active=True, normal_card_rate=0),
        db=db_session,
        current_user=_actor(),
    )

    assert response.name == "Banco Nuevo"
    stored = db_session.get(Bank, response.id)
    assert stored is not None
    assert stored.name == "Banco Nuevo"


def test_update_bank_still_persists_valid_changes(db_session):
    bank = _bank("Banco Inicial")
    db_session.add(bank)
    db_session.commit()

    response = update_bank(
        bank.id,
        BankUpdate(name="  Banco Actualizado  ", active=False),
        db=db_session,
        current_user=_actor(),
    )

    assert response.name == "Banco Actualizado"
    assert response.active is False
    db_session.refresh(bank)
    assert bank.name == "Banco Actualizado"
    assert bank.active is False