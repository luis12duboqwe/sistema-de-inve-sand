from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import SalesProfile
from app.routers import ai_intelligence, ai_slug_integrity, channel_integrations
from app.schemas import AIContextRequest, AIHandleMessageRequest, TrainingSubmission


def _profile(slug: str) -> SalesProfile:
    return SalesProfile(
        name=f"Perfil IA {uuid4().hex}",
        slug=slug,
        tipo="bot_ia",
        active=True,
    )


def test_ai_integrity_routes_are_the_canonical_openapi_handlers(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    expected = {
        "/api/ai/context": "get_ai_context_integrity_",
        "/api/ai/reply": "generate_ai_reply_integrity_",
        "/api/ai/log": "log_interaction_integrity_",
        "/api/ai/training/submit": "submit_training_example_integrity_",
        "/api/ai/handle-message": "handle_message_without_n8n_integrity_",
    }

    for path, operation_prefix in expected.items():
        operation = schema["paths"][path]["post"]
        assert operation["operationId"].startswith(operation_prefix)


def test_ai_context_canonicalizes_unicode_slug_before_legacy_behavior(
    db_session: Session,
    monkeypatch,
) -> None:
    suffix = uuid4().hex
    stored_slug = f"Bót-AI-{suffix}"
    profile = _profile(stored_slug)
    db_session.add(profile)
    db_session.commit()

    observed: dict[str, str] = {}

    def fake_get_ai_context(request, db, auth_context=None):
        observed["slug"] = request.sales_profile_slug
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(ai_slug_integrity.legacy_ai, "get_ai_context", fake_get_ai_context)

    result = ai_slug_integrity.get_ai_context_integrity(
        AIContextRequest(
            sales_profile_slug=f"bÓT-ai-{suffix}",
            customer_phone="50499990000",
            message_content="hola",
        ),
        db_session,
        None,
    )

    assert result.ok is True
    assert observed["slug"] == stored_slug


def test_ai_handle_message_canonicalizes_before_all_legacy_subflows(
    db_session: Session,
    monkeypatch,
) -> None:
    suffix = uuid4().hex
    stored_slug = f"Bót-Handle-{suffix}"
    profile = _profile(stored_slug)
    db_session.add(profile)
    db_session.commit()

    observed: dict[str, str] = {}

    def fake_handle_message(request, db, auth_context=None):
        observed["slug"] = request.sales_profile_slug
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(
        ai_slug_integrity.legacy_ai,
        "handle_message_without_n8n",
        fake_handle_message,
    )

    result = ai_slug_integrity.handle_message_without_n8n_integrity(
        AIHandleMessageRequest(
            sales_profile_slug=f"bÓT-handle-{suffix}",
            customer_phone="50499990001",
            message_content="precio",
        ),
        db_session,
        None,
    )

    assert result.ok is True
    assert observed["slug"] == stored_slug


def test_ai_unknown_profile_keeps_existing_404_contract(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        ai_slug_integrity.get_ai_context_integrity(
            AIContextRequest(
                sales_profile_slug=f"missing-{uuid4().hex}",
                customer_phone="50499990002",
                message_content="hola",
            ),
            db_session,
            None,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Sales Profile not found"


def test_training_unknown_slug_preserves_legacy_nullable_profile_semantics(
    db_session: Session,
    monkeypatch,
) -> None:
    missing_slug = f"missing-training-{uuid4().hex}"
    observed: dict[str, str] = {}

    def fake_submit(submission, db, auth_context=None):
        observed["slug"] = submission.sales_profile_slug
        return {"status": "submitted_for_review"}

    monkeypatch.setattr(
        ai_slug_integrity.legacy_ai,
        "submit_training_example",
        fake_submit,
    )

    result = ai_slug_integrity.submit_training_example_integrity(
        TrainingSubmission(
            sales_profile_slug=missing_slug,
            customer_question="pregunta",
        ),
        db_session,
        None,
    )

    assert result == {"status": "submitted_for_review"}
    assert observed["slug"] == missing_slug


def test_channel_runtime_uses_same_canonical_handle_message_boundary() -> None:
    assert (
        channel_integrations.handle_message_without_n8n
        is ai_slug_integrity.handle_message_without_n8n_integrity
    )
    assert (
        channel_integrations.handle_message_without_n8n
        is not ai_intelligence.handle_message_without_n8n
    )
