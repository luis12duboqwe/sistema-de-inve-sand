from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ProcessedMessage
from app.routers.channel_webhook_integrity import _release_processing_claim


def test_processing_claim_is_released_after_session_enters_failed_state(db_session: Session) -> None:
    message_id = "wamid.FAILED-SESSION-RELEASE"
    db_session.add(
        ProcessedMessage(
            message_id=message_id,
            channel="whatsapp",
            customer_phone="50499993333",
            delivery_status="processing",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    db_session.commit()

    # Force SQLAlchemy into PendingRollback state using the same unique key. The
    # release helper must recover the Session before trying to delete the claim.
    db_session.add(
        ProcessedMessage(
            message_id=message_id,
            channel="whatsapp",
            customer_phone="50499993333",
            delivery_status="processing",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    _release_processing_claim(
        request,  # type: ignore[arg-type]
        db_session,
        message_id=message_id,
        claim_state="database",
    )

    assert (
        db_session.query(ProcessedMessage)
        .filter(ProcessedMessage.message_id == message_id)
        .first()
        is None
    )
