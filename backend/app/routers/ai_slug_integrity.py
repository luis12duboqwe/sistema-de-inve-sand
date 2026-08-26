"""Canonical V2 sales-profile slug boundary for AI endpoints.

The legacy AI router contains mature behavior that should not be duplicated here.
These wrappers only resolve a request/config supplied V2 slug through the
DB-enforced logical identity, replace it with the stored display slug, and then
delegate to the existing implementation.
"""

from __future__ import annotations

from typing import Optional, TypeVar

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers import ai_intelligence as legacy_ai
from app.sales_profile_lookup import find_sales_profile_by_slug
from app.schemas import (
    AIContextRequest,
    AIContextResponse,
    AIHandleMessageRequest,
    AIHandleMessageResponse,
    AIReplyRequest,
    AIReplyResponse,
    InteractionLogCreate,
    TrainingSubmission,
)


router = APIRouter(
    prefix="/api/ai",
    tags=["AI Intelligence"],
    dependencies=[Depends(legacy_ai._ensure_ai_features_enabled)],
)

_RequestT = TypeVar("_RequestT", bound=BaseModel)


def _canonicalize_slug(
    db: Session,
    payload: _RequestT,
    *,
    missing_detail: str | None,
) -> _RequestT:
    """Return the payload with the exact stored display slug when it exists."""
    raw_slug = str(getattr(payload, "sales_profile_slug", "") or "")
    profile = find_sales_profile_by_slug(db, raw_slug)
    if profile is None:
        if missing_detail is not None:
            raise HTTPException(status_code=404, detail=missing_detail)
        return payload

    return payload.model_copy(update={"sales_profile_slug": str(profile.slug)})


@router.post("/context", response_model=AIContextResponse)
def get_ai_context_integrity(
    request: AIContextRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(legacy_ai._require_ai_integration_auth),
):
    canonical = _canonicalize_slug(
        db,
        request,
        missing_detail="Sales Profile not found",
    )
    return legacy_ai.get_ai_context(canonical, db, auth_context)


@router.post("/reply", response_model=AIReplyResponse)
def generate_ai_reply_integrity(
    request: AIReplyRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(legacy_ai._require_ai_integration_auth),
):
    canonical = _canonicalize_slug(
        db,
        request,
        missing_detail="Sales Profile not found",
    )
    return legacy_ai.generate_ai_reply(canonical, db, auth_context)


@router.post("/log")
def log_interaction_integrity(
    log_data: InteractionLogCreate,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(legacy_ai._require_ai_integration_auth),
):
    canonical = _canonicalize_slug(
        db,
        log_data,
        missing_detail="Profile not found",
    )
    return legacy_ai.log_interaction(canonical, db, auth_context)


@router.post("/training/submit")
def submit_training_example_integrity(
    submission: TrainingSubmission,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(legacy_ai._require_ai_integration_auth),
):
    # Legacy semantics deliberately allow an unknown slug and enqueue the item
    # without a sales_profile_id. Canonicalize only when a logical match exists.
    canonical = _canonicalize_slug(db, submission, missing_detail=None)
    return legacy_ai.submit_training_example(canonical, db, auth_context)


@router.post("/handle-message", response_model=AIHandleMessageResponse)
def handle_message_without_n8n_integrity(
    request: AIHandleMessageRequest,
    db: Session = Depends(get_db),
    auth_context: Optional[User] = Depends(legacy_ai._require_ai_integration_auth),
):
    canonical = _canonicalize_slug(
        db,
        request,
        missing_detail="Sales Profile not found",
    )
    return legacy_ai.handle_message_without_n8n(canonical, db, auth_context)


__all__ = [
    "router",
    "get_ai_context_integrity",
    "generate_ai_reply_integrity",
    "log_interaction_integrity",
    "submit_training_example_integrity",
    "handle_message_without_n8n_integrity",
]
