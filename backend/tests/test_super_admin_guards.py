from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers import super_admin
from app.routers.super_admin import (
    ReasonPayload,
    StockAdjustmentRequest,
    _json_load,
    _serialize_stock,
    get_current_superuser_audited,
)


class FakeSession:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_superuser_dependency_returns_superuser_without_audit(monkeypatch):
    user = SimpleNamespace(is_superuser=True, username="root")
    db = FakeSession()
    audit_calls = []
    monkeypatch.setattr(super_admin, "log_audit_event", lambda *args, **kwargs: audit_calls.append((args, kwargs)))

    result = await get_current_superuser_audited(current_user=user, db=db)

    assert result is user
    assert audit_calls == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_superuser_dependency_audits_and_rejects_regular_user(monkeypatch):
    user = SimpleNamespace(is_superuser=False, username="operator")
    db = FakeSession()
    audit_calls = []
    monkeypatch.setattr(super_admin, "log_audit_event", lambda *args, **kwargs: audit_calls.append((args, kwargs)))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_superuser_audited(current_user=user, db=db)

    assert exc_info.value.status_code == 403
    assert "Super Admin" in exc_info.value.detail
    assert db.commits == 1
    assert len(audit_calls) == 1
    _, kwargs = audit_calls[0]
    assert kwargs["action"] == "super_admin.access.denied"
    assert kwargs["entity_type"] == "access"
    assert kwargs["user"] is user


def test_reason_payload_trims_valid_reason_and_rejects_blank_or_too_short_reason():
    assert ReasonPayload(reason="  corrección necesaria  ").reason == "corrección necesaria"

    for reason in ("     ", "abc", " ab "):
        with pytest.raises(ValidationError):
            ReasonPayload(reason=reason)


def test_stock_adjustment_enforces_reserved_not_above_available():
    valid = StockAdjustmentRequest(
        reason="Ajuste por conteo físico",
        product_id=1,
        location_id=2,
        cantidad_disponible=5,
        cantidad_reservada=5,
        cantidad_defectuosa=1,
    )
    assert valid.cantidad_reservada == 5

    with pytest.raises(ValidationError) as exc_info:
        StockAdjustmentRequest(
            reason="Ajuste por conteo físico",
            product_id=1,
            location_id=2,
            cantidad_disponible=4,
            cantidad_reservada=5,
        )

    assert "reservado no puede ser mayor" in str(exc_info.value)


def test_json_load_preserves_non_json_and_parses_json_values():
    assert _json_load(None) is None
    assert _json_load("") is None
    assert _json_load('{"ok": true}') == {"ok": True}
    assert _json_load("texto legado") == "texto legado"


def test_serialize_stock_returns_stable_snapshot_shape():
    assert _serialize_stock(None) is None

    stock = SimpleNamespace(
        id=9,
        product_id=3,
        location_id=2,
        cantidad_disponible=7,
        cantidad_reservada=1,
        cantidad_defectuosa=2,
    )

    assert _serialize_stock(stock) == {
        "id": 9,
        "product_id": 3,
        "location_id": 2,
        "cantidad_disponible": 7,
        "cantidad_reservada": 1,
        "cantidad_defectuosa": 2,
    }
