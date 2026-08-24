import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models import Bank, User
from app.routers.financing import create_bank, update_bank
from app.schemas import BankCreate, BankUpdate
from app.utils.bank_names import normalize_bank_name


def _actor() -> User:
    return User(
        username="finance-admin",
        email="finance-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "B\u200bAC",  # zero-width space (Cf)
        "B\u00adAC",  # soft hyphen (Cf)
        "B\u0007AC",  # control character (Cc)
    ],
)
def test_create_bank_rejects_unsafe_unicode_as_400(db_session, unsafe_name):
    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name=unsafe_name, active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "Unicode no permitidos" in exc_info.value.detail
    assert db_session.query(Bank).count() == 0


def test_unpaired_surrogate_is_rejected_before_utf8_hashing():
    unsafe_name = "\ud800A"

    with pytest.raises(ValidationError):
        BankCreate(name=unsafe_name, active=True, normal_card_rate=0)

    with pytest.raises(ValueError, match="Unicode no permitidos"):
        normalize_bank_name(unsafe_name)


def test_update_bank_rejects_invisible_unicode_and_preserves_name(db_session):
    bank = Bank(name="Banco Inicial", active=True, normal_card_rate=0)
    db_session.add(bank)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_bank(
            bank.id,
            BankUpdate(name="Banco\u200bInicial"),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    db_session.refresh(bank)
    assert bank.name == "Banco Inicial"
