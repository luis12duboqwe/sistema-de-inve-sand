from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import Bank, FinancingOption
from app.routers.financing import create_bank, create_option
from app.schemas.finance import BankCreate, FinancingOptionCreate
from app.utils.order_financing import compute_financing_from_payload
from app.utils.s3_storage import validate_media_upload


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=1, username="hardening", is_active=True, is_superuser=True, role=None)


def test_new_financing_rejects_inactive_bank(db_session):
    bank = Bank(name=f"Banco Inactivo {uuid4().hex}", active=False, normal_card_rate=Decimal("0.03"))
    db_session.add(bank)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        compute_financing_from_payload(
            db_session,
            {"bank_id": bank.id, "months": 0, "down_payment": 0},
            "tarjeta",
            Decimal("10000.00"),
            Decimal("0.00"),
        )

    assert exc_info.value.status_code == 400
    assert "inactivo" in str(exc_info.value.detail).lower()


def test_create_bank_rejects_duplicate_financing_terms(db_session):
    payload = BankCreate(
        name=f"Banco Duplicado {uuid4().hex}",
        normal_card_rate=Decimal("0.03"),
        financing_options=[
            FinancingOptionCreate(months=12, rate=Decimal("0.10"), active=True),
            FinancingOptionCreate(months=12, rate=Decimal("0.12"), active=True),
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        create_bank(payload, db_session, _user())

    assert exc_info.value.status_code == 400
    assert "mismo plazo" in str(exc_info.value.detail).lower()


def test_create_option_rejects_existing_term(db_session):
    bank = Bank(name=f"Banco Plazo {uuid4().hex}", active=True, normal_card_rate=Decimal("0.03"))
    db_session.add(bank)
    db_session.flush()
    db_session.add(FinancingOption(bank_id=bank.id, months=12, rate=Decimal("0.10"), active=True))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_option(
            FinancingOptionCreate(months=12, rate=Decimal("0.11"), active=True),
            int(bank.id),
            db_session,
            _user(),
        )

    assert exc_info.value.status_code == 409


def test_media_validation_accepts_supported_signature():
    family, extension = validate_media_upload(
        b"\xff\xd8\xff\xe0" + b"jpeg-payload",
        "image/jpeg",
    )
    assert family == "image"
    assert extension == ".jpg"


def test_media_validation_rejects_active_document_disguised_as_image():
    with pytest.raises(ValueError):
        validate_media_upload(
            b"<html><script>alert('x')</script></html>",
            "image/jpeg",
        )


def test_media_validation_rejects_content_type_mismatch():
    with pytest.raises(ValueError):
        validate_media_upload(
            b"\x89PNG\r\n\x1a\n" + b"png-payload",
            "image/jpeg",
        )
