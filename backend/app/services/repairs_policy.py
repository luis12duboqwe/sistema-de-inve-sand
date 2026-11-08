"""Repair status guards; no customer messages or payments."""
from decimal import Decimal, InvalidOperation
import re

class InvalidRepairTransition(ValueError):
    pass

ALLOWED={
 "received":("diagnosing","cancelled"),
 "diagnosing":("awaiting_approval","cancelled"),
 "awaiting_approval":("approved","cancelled"),
 "approved":("awaiting_parts","repairing","cancelled"),
 "awaiting_parts":("repairing","cancelled"),
 "repairing":("quality_check",),
 "quality_check":("repairing","ready"),
 "ready":("delivered",),
 "delivered":(),
 "cancelled":(),
}
ISSUE_CATEGORIES={"screen","battery","charging","software","camera",
                  "water_damage","micro_soldering","other"}

def checked_price(value):
    try:amount=Decimal(str(value))
    except (TypeError,ValueError,InvalidOperation):
        raise InvalidRepairTransition("valid quote required")
    if not amount.is_finite() or amount<=0 or amount>Decimal("1000000") or amount.as_tuple().exponent < -2:
        raise InvalidRepairTransition("quote outside permitted range")
    return amount

def state_transition(old,next_state,*,existing_quote=None,
                     quote=None,approval_reference=None,
                     parts_available=None,qa_passed=None,existing_qa_passed=False):
    """Returns only case-field updates after authorization by superuser.

    Approval_reference is proof-of-review identifier recorded by a human.
    This function cannot verify customer consent; integration must do so.
    """
    if old not in ALLOWED or next_state not in ALLOWED[old]:
        raise InvalidRepairTransition("transition not permitted")
    result={"status":next_state}
    if next_state=="awaiting_approval":
        result["quote_amount"]=checked_price(quote)
        result["qa_passed"]=False
    if next_state=="approved":
        if existing_quote is None:
            raise InvalidRepairTransition("quote absent")
        if (not isinstance(approval_reference,str) or
            not re.fullmatch(r"[A-Z0-9-]{12,64}",approval_reference)):
            raise InvalidRepairTransition("verified human approval reference required")
        result["approval_reference_digest"]=__import__("hashlib").sha256(
                    approval_reference.encode()).hexdigest()
        result["quote_approved"]=True
    if next_state=="awaiting_parts" and parts_available is not False:
        raise InvalidRepairTransition("parts shortage must be confirmed")
    if next_state=="repairing":
        if old in ("approved","awaiting_parts") and parts_available is not True:
            raise InvalidRepairTransition("parts availability must be confirmed")
        result["parts_available"]=True
        result["qa_passed"]=False
    if next_state=="quality_check":
        result["qa_passed"]=False
    if next_state=="ready":
        if qa_passed is not True:
            raise InvalidRepairTransition("QA passed by human is mandatory")
        result["qa_passed"]=True
    if next_state=="delivered" and existing_qa_passed is not True:
        raise InvalidRepairTransition("no delivery without QA")
    return result
