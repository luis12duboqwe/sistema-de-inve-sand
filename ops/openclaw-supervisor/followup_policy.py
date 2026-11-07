"""Deterministic, fail-closed commercial follow-up *planning*.

There are intentionally NO network calls, Chatwoot writes or send functions.
All results are advisory until channel, consent and a human-approved release are verified.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Evidence:
    conversation_id: int
    quote_id: int | None
    minutes_since_quote: float | None
    open: bool
    explicit_consent: bool
    opted_out: bool
    human_takeover: bool
    human_replied_since_quote: bool
    incoming_after_quote_other_than_consent: bool
    followed_quote_id: int | None
    transport_online: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any], transport_online: bool) -> "Evidence":
        """Strict type checks prevent truthy strings like 'false' from authorizing a send."""
        flags = ("open", "explicit_consent", "opted_out", "human_takeover",
                 "human_replied_since_quote", "incoming_after_quote_other_than_consent")
        if any(type(data.get(k)) is not bool for k in flags):
            raise ValueError("follow-up consent/safety flag missing or not boolean")
        conv = data.get("conversation_id")
        quote = data.get("quote_id")
        followed = data.get("followed_quote_id")
        minutes = data.get("minutes_since_quote")
        if type(conv) is not int or conv < 1:
            raise ValueError("invalid conversation")
        for x in (quote, followed):
            if x is not None and (type(x) is not int or x < 1):
                raise ValueError("invalid quote identifier")
        if minutes is not None and (type(minutes) not in (int, float) or
                                    not -1 <= minutes <= 525600):
            raise ValueError("invalid quote timestamp")
        if type(transport_online) is not bool:
            raise ValueError("transport state is not authoritative")
        return cls(conversation_id=conv, quote_id=quote,
                   minutes_since_quote=minutes, transport_online=transport_online,
                   followed_quote_id=followed, **{k:data[k] for k in flags})

def decide(e: Evidence) -> str:
    """Return a review category, NEVER an authorization to contact a buyer."""
    if e.quote_id is None or e.minutes_since_quote is None:
        return "no_verified_quote"
    if not e.open:
        return "closed"
    if e.opted_out:
        return "blocked_optout"
    if e.human_takeover or e.human_replied_since_quote:
        return "blocked_human"
    if e.followed_quote_id == e.quote_id:
        return "blocked_duplicate"
    if e.incoming_after_quote_other_than_consent:
        return "blocked_customer_replied"
    if not e.explicit_consent:
        return "needs_consent"
    if e.minutes_since_quote < 120:
        return "not_due"
    if e.minutes_since_quote > 1440:
        return "expired"
    if not e.transport_online:
        return "blocked_test_transport"
    return "ready_for_manual_review"

def propose(records: list[dict], transport_online: bool) -> dict:
    """Aggregate minimal evidence; no message content or PII survives."""
    by_status: dict[str, int] = {}
    cases: list[dict[str, int | str | bool]] = []
    for record in records:
        evidence = Evidence.from_mapping(record, transport_online)
        status = decide(evidence)
        by_status[status] = by_status.get(status, 0) + 1
        if status in ("ready_for_manual_review", "blocked_test_transport", "needs_consent"):
            cases.append({"conversation_id":evidence.conversation_id,
                          "quote_id":evidence.quote_id,
                          "status":status, "requires_human_approval":True})
    return {"mode":"proposals_only","public_messages_sent":0,
            "eligible_to_send_automatically":0,
            "scanned_quotes":len(records),"by_status":by_status,
            "cases":sorted(cases,key=lambda x: x["conversation_id"])}
