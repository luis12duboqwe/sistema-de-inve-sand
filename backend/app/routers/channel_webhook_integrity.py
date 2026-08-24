"""Canonical webhook delivery guards for Meta-backed sales channels."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import logging
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config_production import prod_settings
from app.database import get_db
from app.models import ProcessedMessage, SalesProfile
from app.routers import channel_integrations as legacy_channels
from app.schemas import AIHandleMessageRequest


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/channels", tags=["Channel Integrations"])
ClaimState = Literal["duplicate", "database", "retry_delivery", "memory", "untracked"]
_PENDING_DELIVERY_TTL_SECONDS = 24 * 60 * 60


def _message_ttl_seconds() -> int:
    return max(60, int(getattr(prod_settings, "CHANNEL_MESSAGE_TTL_SECONDS", 600) or 600))


def _claim_message(
    request: Request,
    db: Session,
    *,
    message_id: str | None,
    channel: str,
    customer_phone: str | None,
) -> ClaimState:
    """Atomically claim new work or a cached reply that still needs delivery."""
    if not message_id:
        return "untracked"

    now = datetime.now(UTC)
    try:
        # Pending/ambiguous rows are intentionally durable. Expiring them could
        # replay AI/business side effects when a provider sends a late retry.
        db.query(ProcessedMessage).filter(
            ProcessedMessage.expires_at <= now,
            or_(
                ProcessedMessage.delivery_status.is_(None),
                ProcessedMessage.delivery_status.in_(["processing", "delivered"]),
            ),
        ).delete(synchronize_session=False)
        db.add(
            ProcessedMessage(
                message_id=message_id,
                channel=channel,
                customer_phone=customer_phone,
                delivery_status="processing",
                expires_at=now + timedelta(seconds=_message_ttl_seconds()),
            )
        )
        db.commit()
        return "database"
    except IntegrityError:
        db.rollback()
        try:
            existing = (
                db.query(ProcessedMessage)
                .filter(ProcessedMessage.message_id == message_id)
                .with_for_update()
                .first()
            )
            if existing is None:
                return "duplicate"

            state = str(existing.delivery_status or "").strip().lower()
            if state == "pending_delivery" and existing.reply_text:
                # Only a confirmed send failure is auto-retryable. An ambiguous
                # `delivering` row might already have been accepted by Meta.
                existing.delivery_status = "delivering"
                existing.processed_at = now
                existing.expires_at = now + timedelta(seconds=_PENDING_DELIVERY_TTL_SECONDS)
                db.commit()
                return "retry_delivery"

            db.rollback()
            return "duplicate"
        except Exception:
            db.rollback()
            logger.exception("Could not inspect existing webhook delivery claim")
            return "duplicate"
    except Exception:
        db.rollback()
        logger.exception("Persistent webhook deduplication unavailable; using memory fallback")
        return "duplicate" if legacy_channels._is_duplicate_message(request, message_id) else "memory"


def _release_processing_claim(
    request: Request,
    db: Session,
    *,
    message_id: str | None,
    claim_state: ClaimState,
) -> None:
    """Release only work that failed before AI/business side effects completed."""
    if not message_id:
        return

    if claim_state == "database":
        # A failed SQLAlchemy flush/commit leaves the Session unusable until a
        # rollback. Roll back first so the claim deletion itself can succeed.
        db.rollback()
        try:
            db.query(ProcessedMessage).filter(
                ProcessedMessage.message_id == message_id,
                ProcessedMessage.delivery_status == "processing",
            ).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not release failed webhook processing claim %s", message_id)
        return

    if claim_state == "memory":
        cache = getattr(request.app.state, "channel_processed_messages", None)
        if isinstance(cache, dict):
            cache.pop(message_id, None)


def _retain_claim_for_manual_recovery(
    db: Session,
    *,
    message_id: str | None,
    claim_state: ClaimState,
) -> None:
    """Quarantine an ambiguous post-AI failure instead of replaying side effects."""
    if claim_state != "database" or not message_id:
        return

    db.rollback()
    try:
        claim = (
            db.query(ProcessedMessage)
            .filter(ProcessedMessage.message_id == message_id)
            .with_for_update()
            .first()
        )
        if claim:
            now = datetime.now(UTC)
            claim.delivery_status = "manual_recovery"
            claim.processed_at = now
            claim.expires_at = now + timedelta(seconds=_PENDING_DELIVERY_TTL_SECONDS)
            db.commit()
            return
        db.rollback()
    except Exception:
        db.rollback()
        logger.exception("Could not quarantine ambiguous webhook claim %s", message_id)


def _store_reply_for_delivery(
    db: Session,
    *,
    message_id: str | None,
    claim_state: ClaimState,
    sales_profile_slug: str,
    reply_text: str,
) -> None:
    """Persist the generated reply before contacting Meta."""
    if claim_state != "database" or not message_id:
        return

    now = datetime.now(UTC)
    claim = (
        db.query(ProcessedMessage)
        .filter(ProcessedMessage.message_id == message_id)
        .with_for_update()
        .first()
    )
    if claim is None:
        raise RuntimeError("Webhook delivery claim disappeared before reply persistence")

    profile = db.query(SalesProfile).filter(SalesProfile.slug == sales_profile_slug).first()
    claim.sales_profile_id = profile.id if profile else None
    claim.reply_text = reply_text
    claim.delivery_status = "delivering"
    claim.processed_at = now
    claim.expires_at = now + timedelta(seconds=_PENDING_DELIVERY_TTL_SECONDS)
    db.commit()


def _mark_delivery_failed(
    request: Request,
    db: Session,
    *,
    message_id: str | None,
    claim_state: ClaimState,
) -> None:
    if not message_id:
        return

    if claim_state in {"database", "retry_delivery"}:
        # Context resolution can itself fail through SQLAlchemy. Recover the
        # Session before querying the durable cached reply.
        db.rollback()
        try:
            claim = (
                db.query(ProcessedMessage)
                .filter(ProcessedMessage.message_id == message_id)
                .with_for_update()
                .first()
            )
            if claim and claim.reply_text:
                now = datetime.now(UTC)
                claim.delivery_status = "pending_delivery"
                claim.processed_at = now
                claim.expires_at = now + timedelta(seconds=_PENDING_DELIVERY_TTL_SECONDS)
                db.commit()
                return
            db.rollback()
        except Exception:
            db.rollback()
            logger.exception("Could not mark webhook reply pending for retry %s", message_id)
        return

    # With no persistent cache we cannot prove that replaying AI is safe. Keep
    # the in-memory marker instead of deliberately duplicating internal effects.
    if claim_state == "memory":
        logger.error(
            "Webhook reply delivery failed while persistent dedupe was unavailable; "
            "memory claim retained to prevent immediate AI replay for %s",
            message_id,
        )


def _mark_delivered(
    db: Session,
    *,
    message_id: str | None,
    claim_state: ClaimState,
) -> None:
    if claim_state not in {"database", "retry_delivery"} or not message_id:
        return

    db.rollback()
    try:
        claim = (
            db.query(ProcessedMessage)
            .filter(ProcessedMessage.message_id == message_id)
            .with_for_update()
            .first()
        )
        if claim:
            now = datetime.now(UTC)
            claim.delivery_status = "delivered"
            claim.reply_text = None
            claim.processed_at = now
            claim.expires_at = now + timedelta(seconds=_message_ttl_seconds())
            db.commit()
            return
        db.rollback()
    except Exception:
        db.rollback()
        # Meta may already have accepted the message. Leave `delivering` as an
        # ambiguous, non-auto-retryable state rather than risk a duplicate reply.
        logger.exception("Could not mark webhook reply delivered %s", message_id)


def _prepare_incoming_event(
    event: legacy_channels.IncomingEvent,
    db: Session,
) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    """Run AI/business side effects once, but defer external delivery."""
    sales_profile_slug, integration_config = legacy_channels._resolve_profile_for_event(db, event)
    ai_payload = AIHandleMessageRequest(
        sales_profile_slug=sales_profile_slug,
        customer_phone=event.customer_id,
        customer_name=event.customer_name,
        message_content=event.text,
        order_intent=None,
    )
    ai_result = legacy_channels.handle_message_without_n8n(ai_payload, db, None)
    result: Dict[str, Any] = {
        "channel": event.channel,
        "sales_profile_slug": sales_profile_slug,
        "account_id": event.account_id,
        "customer_id": event.customer_id,
        "external_message_id": event.external_message_id,
        "reply_preview": ai_result.reply[:120],
        "tokens_used": ai_result.tokens_used,
    }
    return result, ai_result.reply, integration_config


def _cached_delivery_context(
    event: legacy_channels.IncomingEvent,
    db: Session,
) -> tuple[ProcessedMessage, str, Dict[str, Any]]:
    claim = db.query(ProcessedMessage).filter(
        ProcessedMessage.message_id == event.external_message_id
    ).first()
    if claim is None or not claim.reply_text:
        raise HTTPException(status_code=409, detail="No existe respuesta pendiente para reintentar")

    profile = None
    if claim.sales_profile_id:
        profile = db.query(SalesProfile).filter(SalesProfile.id == claim.sales_profile_id).first()
    if profile:
        return claim, str(profile.slug), legacy_channels._extract_channel_integration(profile, event.channel)

    sales_profile_slug, integration_config = legacy_channels._resolve_profile_for_event(db, event)
    return claim, sales_profile_slug, integration_config


async def _retry_cached_delivery(
    event: legacy_channels.IncomingEvent,
    request: Request,
    db: Session,
) -> Dict[str, Any]:
    try:
        claim, sales_profile_slug, integration_config = _cached_delivery_context(event, db)
        reply_text = str(claim.reply_text or "")
        await legacy_channels._send_channel_reply(
            event.channel,
            event.customer_id,
            reply_text,
            integration_config,
        )
    except Exception:
        # `_claim_message` already moved pending_delivery -> delivering. Any
        # context/send failure must restore the cached reply to pending_delivery.
        _mark_delivery_failed(
            request,
            db,
            message_id=event.external_message_id,
            claim_state="retry_delivery",
        )
        raise

    _mark_delivered(
        db,
        message_id=event.external_message_id,
        claim_state="retry_delivery",
    )
    return {
        "channel": event.channel,
        "sales_profile_slug": sales_profile_slug,
        "account_id": event.account_id,
        "customer_id": event.customer_id,
        "external_message_id": event.external_message_id,
        "reply_preview": reply_text[:120],
        "tokens_used": 0,
        "delivery_retry": True,
    }


async def _handle_channel_webhook_integrity(
    channel: str,
    request: Request,
    db: Session,
) -> Dict[str, Any] | JSONResponse:
    raw_body = await request.body()
    legacy_channels._verify_meta_signature(
        raw_body,
        request.headers.get("X-Hub-Signature-256"),
    )

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError as exc:
        return JSONResponse(status_code=400, content={"detail": f"JSON inválido: {exc}"})

    events = legacy_channels._normalize_channel_payload(payload, channel)
    processed: list[Dict[str, Any]] = []
    skipped_duplicates = 0
    failed: list[Dict[str, str]] = []

    for event in events:
        claim_state = _claim_message(
            request,
            db,
            message_id=event.external_message_id,
            channel=channel,
            customer_phone=event.customer_id,
        )
        if claim_state == "duplicate":
            skipped_duplicates += 1
            continue

        if claim_state == "retry_delivery":
            try:
                processed.append(await _retry_cached_delivery(event, request, db))
            except Exception as exc:
                logger.warning("Cached webhook delivery retry failed for %s: %s", channel, exc)
                failed.append({"customer_id": event.customer_id, "error": str(getattr(exc, "detail", exc))})
            continue

        ai_completed = False
        reply_prepared = False
        try:
            result, reply_text, integration_config = _prepare_incoming_event(event, db)
            ai_completed = True
            _store_reply_for_delivery(
                db,
                message_id=event.external_message_id,
                claim_state=claim_state,
                sales_profile_slug=str(result["sales_profile_slug"]),
                reply_text=reply_text,
            )
            reply_prepared = True

            await legacy_channels._send_channel_reply(
                event.channel,
                event.customer_id,
                reply_text,
                integration_config,
            )
            _mark_delivered(
                db,
                message_id=event.external_message_id,
                claim_state=claim_state,
            )
            processed.append(result)
        except Exception as exc:
            logger.warning("Webhook %s message failed: %s", channel, exc)
            if reply_prepared:
                _mark_delivery_failed(
                    request,
                    db,
                    message_id=event.external_message_id,
                    claim_state=claim_state,
                )
            elif not ai_completed:
                _release_processing_claim(
                    request,
                    db,
                    message_id=event.external_message_id,
                    claim_state=claim_state,
                )
            else:
                _retain_claim_for_manual_recovery(
                    db,
                    message_id=event.external_message_id,
                    claim_state=claim_state,
                )
                logger.error(
                    "Webhook %s completed AI but could not persist reply for %s; "
                    "claim quarantined for manual recovery",
                    channel,
                    event.external_message_id,
                )
            failed.append({"customer_id": event.customer_id, "error": str(getattr(exc, "detail", exc))})

    response: Dict[str, Any] = {
        "status": "ok" if not failed else "retry_required",
        "channel": channel,
        "processed_count": len(processed),
        "skipped_duplicates": skipped_duplicates,
        "failed_count": len(failed),
        "processed": processed,
        "failed": failed,
    }
    if failed:
        return JSONResponse(status_code=502, content=response)
    return response


@router.post("/whatsapp/webhook")
async def whatsapp_webhook_integrity(request: Request, db: Session = Depends(get_db)):
    return await _handle_channel_webhook_integrity("whatsapp", request, db)


@router.post("/messenger/webhook")
async def messenger_webhook_integrity(request: Request, db: Session = Depends(get_db)):
    return await _handle_channel_webhook_integrity("messenger", request, db)


@router.post("/instagram/webhook")
async def instagram_webhook_integrity(request: Request, db: Session = Depends(get_db)):
    return await _handle_channel_webhook_integrity("instagram", request, db)
