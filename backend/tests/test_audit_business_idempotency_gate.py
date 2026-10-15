"""A rejected network response cannot be safely retried unless it has a stable identity."""
import pytest
from fastapi import HTTPException

from app.models import BusinessRequestKey
from app.utils.business_idempotency import claim_business_request, save_business_response


def test_business_creation_requires_stable_key_in_production_gate(db_session):
    with pytest.raises(HTTPException) as error:
        claim_business_request(
            db_session,
            key=None, require_key=True, identity_id=19,
            endpoint="POST /api/orders", payload={"total": 100},
        )
    assert error.value.status_code == 428
    assert db_session.query(BusinessRequestKey).count() == 0


def test_business_creation_key_replays_exact_result(db_session):
    options = dict(
        key="business-replay-2026", require_key=True,
        identity_id=19, endpoint="POST /api/orders",
        payload={"items": [{"id": 7}], "total": 100},
    )
    first = claim_business_request(db_session, **options)
    assert first.entry is not None
    assert first.replay is None
    save_business_response(first, {"id": 47, "total": 100})
    db_session.commit()

    again = claim_business_request(db_session, **options)
    assert again.replay == {"id": 47, "total": 100}
    assert again.entry is None

    with pytest.raises(HTTPException) as error:
        claim_business_request(db_session, **{**options, "payload": {"total": 200}})
    assert error.value.status_code == 409


def test_nonproduction_legacy_calls_can_use_unkeyed_requests(db_session):
    claim = claim_business_request(
        db_session,
        key=None, require_key=False, identity_id=5,
        endpoint="POST /api/stock-transfers", payload={"cantidad": 1},
    )
    assert claim.entry is None and claim.replay is None
