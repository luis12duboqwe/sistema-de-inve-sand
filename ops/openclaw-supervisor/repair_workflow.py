#!/usr/bin/env python3
"""Pure, offline repair-ticket workflow for SoftMobile.

MVP domain rules. This module does not connect to customer data, workers,
inventories, payments or WhatsApp; no tickets can be marked real by this lab.
Human approval and technician decisions are deliberately required.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Optional
import re
import uuid

STATES=frozenset(("received","diagnosing","awaiting_approval",
         "approved","awaiting_parts","repairing","quality_check",
         "ready","delivered","cancelled"))
MOVES={
    "received":{"diagnosing","cancelled"},
    "diagnosing":{"awaiting_approval","cancelled"},
    "awaiting_approval":{"approved","cancelled"},
    "approved":{"awaiting_parts","repairing","cancelled"},
    "awaiting_parts":{"repairing","cancelled"},
    "repairing":{"quality_check"},
    "quality_check":{"ready","repairing"},
    "ready":{"delivered"},
    "delivered":set(),
    "cancelled":set(),
}
STAFF={"technician","human_supervisor"}
SENSITIVE=re.compile(r"\b(?:\d{8,}|\w+@\w+\.\w+)\b")
class TransitionDenied(ValueError):pass

@dataclass(frozen=True)
class Ticket:
    case_id: str
    stage: str = "received"
    revision: int = 0
    quote_hnl: Optional[str] = None
    quote_approved: bool = False
    parts_available: Optional[bool] = None
    passed_quality_check: bool = False
    event_ids: tuple[str,...] = ()
    history: tuple[tuple[str,str],...] = ()
    synthetic_only: bool = True

def create(case_id=None):
    identifier=("SYN-"+uuid.uuid4().hex[:12].upper()) if case_id is None else case_id
    if not re.fullmatch(r"SYN-[A-Z0-9]{5,24}",identifier):
        raise TransitionDenied("synthetic case IDs only")
    return Ticket(identifier)

def money(amount):
    if amount is None:raise TransitionDenied("quote mandatory")
    try: d=Decimal(str(amount))
    except (InvalidOperation,TypeError,ValueError):raise TransitionDenied("invalid quote")
    if not d.is_finite() or d<=0 or d>Decimal("1000000") or d.as_tuple().exponent<-2:
        raise TransitionDenied("invalid quote")
    return f"{d:.2f}"

def advance(ticket,to,actor,event_id,expected_revision,quote=None,
            documented_human_approval=False,parts_available=None,
            qa_passed=None):
    if not isinstance(ticket,Ticket) or not ticket.synthetic_only:
        raise TransitionDenied("only offline synthetic repairs")
    if not isinstance(event_id,str) or not re.fullmatch(r"[a-z0-9-]{8,60}",event_id):
        raise TransitionDenied("invalid event ID")
    if event_id in ticket.event_ids:
        # Repeated delivery is safe only if it represents the same transition.
        if ticket.history[ticket.event_ids.index(event_id)][1]!=to:
            raise TransitionDenied("replayed event conflicts with original")
        return ticket
    if (type(expected_revision) is not int or expected_revision!=ticket.revision):
        raise TransitionDenied("stale revision")
    if to not in STATES or to not in MOVES.get(ticket.stage,set()):
        raise TransitionDenied("invalid state transition")
    if actor not in STAFF:
        raise TransitionDenied("automatic actor cannot approve repairs")
    if to=="diagnosing" and actor!="technician":
        raise TransitionDenied("only technician diagnoses")
    if to=="awaiting_approval":
        if actor!="technician":raise TransitionDenied("only technician quotes")
        validated=money(quote)
        ticket=replace(ticket,quote_hnl=validated,quote_approved=False)
    if to=="approved":
        if actor!="human_supervisor" or documented_human_approval is not True:
            raise TransitionDenied("human approval required")
        if ticket.quote_hnl is None:
            raise TransitionDenied("cannot approve an unpriced repair")
        ticket=replace(ticket,quote_approved=True)
    if to in ("awaiting_parts","repairing"):
        if not ticket.quote_approved:
            raise TransitionDenied("repair without verified quote approval")
        if to=="awaiting_parts" and parts_available is not False:
            raise TransitionDenied("missing part must be explicitly confirmed")
        if to=="repairing" and parts_available is not True:
            raise TransitionDenied("parts/conditions must be confirmed")
        ticket=replace(ticket,parts_available=parts_available)
    if to=="quality_check":
        if actor!="technician":raise TransitionDenied("only technician requests QA")
        ticket=replace(ticket,passed_quality_check=False)
    if to=="ready":
        if actor!="human_supervisor" or qa_passed is not True:
            raise TransitionDenied("supervisor QA approval required")
        ticket=replace(ticket,passed_quality_check=True)
    if to=="delivered":
        if actor!="human_supervisor" or not ticket.passed_quality_check:
            raise TransitionDenied("delivery requires approved QA and human supervisor")
    if to=="cancelled" and actor!="human_supervisor":
        raise TransitionDenied("cancellation requires supervisor")
    return replace(ticket,stage=to,revision=ticket.revision+1,
         event_ids=(*ticket.event_ids,event_id),
         history=(*ticket.history,(ticket.stage,to)))

def suggested_followup(ticket):
    if not ticket.synthetic_only:raise TransitionDenied("only training")
    messages={
      "received":"await technician intake",
      "diagnosing":"await technical diagnostics",
      "awaiting_approval":"human review of quote required",
      "approved":"technician may schedule",
      "awaiting_parts":"internal restocking suggestion only",
      "repairing":"wait for technical work",
      "quality_check":"supervisor must confirm QA",
      "ready":"human pickup coordination needed, no messages sent",
      "delivered":"closed after human delivery",
      "cancelled":"closed by human supervisor"}
    return {"case_id":ticket.case_id,"stage":ticket.stage,
            "next_action":messages[ticket.stage],
            "contact_customer_automatically":False,
            "automated_payment":False,"inventory_mutations":False}

def run_synthetic_cases(n=60):
    if type(n) is not int or not 1<=n<=500:raise ValueError("invalid count")
    outcomes=[]
    for i in range(n):
        t=create("SYN-"+f"{i+1:08d}")
        transitions=[
          ("diagnosing","technician",{}),
          ("awaiting_approval","technician",{"quote":str(350+i%20*75)}),
          ("approved","human_supervisor",{"documented_human_approval":True})
        ]
        if i%5==0:
            transitions.append(("awaiting_parts","technician",{"parts_available":False}))
        transitions.extend([
          ("repairing","technician",{"parts_available":True}),
          ("quality_check","technician",{}),
          ("ready","human_supervisor",{"qa_passed":True}),
          ("delivered","human_supervisor",{})
        ])
        for j,(to,actor,kw) in enumerate(transitions):
            t=advance(t,to,actor,f"event-{i:03d}-{j:02d}",t.revision,**kw)
        outcomes.append(t.stage=="delivered" and t.synthetic_only and
                        len(t.history)==len(transitions))
    return {"environment":"SYNTHETIC_OFFLINE_ONLY","cases":n,
            "passed":sum(outcomes),"failed":n-sum(outcomes),
            "real_repairs":0,"public_messages_sent":0,
            "payments_initiated":0,"real_inventory_mutations":0,
            "source_connected":False}
