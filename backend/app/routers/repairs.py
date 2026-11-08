"""Admin-only, feature-gated repair intake API. No WhatsApp or payments."""
from __future__ import annotations
from datetime import datetime,timezone
import os
import uuid
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.auth import get_current_superuser
from app.database import get_db
from app.models.location import Location
from app.models.rbac import User
from app.utils.location_access import user_has_location_access
from app.models.repairs import RepairCase,RepairEvent
from app.schemas.repairs import (CreateRepairCase,RepairCaseView,
                                  RepairTransitionRequest,RepairEventView,
                                  RepairAssignmentRequest)
from app.services.repairs_policy import state_transition,InvalidRepairTransition

def require_repairs_enabled():
    # Off by default, including if absent in production.
    if os.environ.get("SOFTMOBILE_REPAIRS_ENABLED","").strip().lower()!="true":
        raise HTTPException(status_code=503,detail="Repair intake is not enabled")

router=APIRouter(prefix="/api/repairs",tags=["Internal Repair Intake"],
                 dependencies=[Depends(require_repairs_enabled),
                               Depends(get_current_superuser)])

def case_or_404(db:Session,repair_id:int,lock=False):
    q=db.query(RepairCase).filter(RepairCase.id==repair_id)
    if lock:q=q.with_for_update()
    case=q.first()
    if case is None:raise HTTPException(404,"Repair case not found")
    return case

@router.post("",status_code=201,response_model=RepairCaseView)
def create_repair(payload:CreateRepairCase,
                  db:Session=Depends(get_db),
                  actor=Depends(get_current_superuser)):
    loc=db.query(Location).filter(Location.id==payload.location_id,
                                  Location.activo.is_(True)).first()
    if loc is None:raise HTTPException(422,"Active location required")
    ref="RPR-"+uuid.uuid4().hex[:14].upper()
    case=RepairCase(external_reference=ref,location_id=payload.location_id,
                    device_model=payload.device_model,
                    issue_category=payload.issue_category,
                    status="received",revision=0,quote_approved=False,qa_passed=False)
    db.add(case);db.commit();db.refresh(case)
    return case

@router.get("",response_model=list[RepairCaseView])
def list_repairs(status:str|None=None,
                 location_id:int|None=Query(None,gt=0),
                 limit:int=Query(50,ge=1,le=100),
                 db:Session=Depends(get_db),
                 actor=Depends(get_current_superuser)):
    q=db.query(RepairCase)
    if status:
        if status not in ("received","diagnosing","awaiting_approval",
                         "approved","awaiting_parts","repairing",
                         "quality_check","ready","delivered","cancelled"):
            raise HTTPException(422,"Invalid status")
        q=q.filter(RepairCase.status==status)
    if location_id:q=q.filter(RepairCase.location_id==location_id)
    return q.order_by(RepairCase.id.desc()).limit(limit).all()

@router.get("/overview")
def overview(db:Session=Depends(get_db),
             actor=Depends(get_current_superuser)):
    from sqlalchemy import func
    rows=db.query(RepairCase.status,func.count(RepairCase.id)).group_by(RepairCase.status).all()
    # Anonymous business stats only; not verified repairs if this feature is off.
    return {"by_status":{status:int(n) for status,n in rows},
            "records":sum(int(n) for _,n in rows),
            "public_notifications_sent":0,
            "payments_collected":0}

@router.get("/{repair_id}",response_model=RepairCaseView)
def get_repair(repair_id:int,db:Session=Depends(get_db),
               actor=Depends(get_current_superuser)):
    return case_or_404(db,repair_id)

@router.get("/{repair_id}/events",response_model=list[RepairEventView])
def repair_events(repair_id:int,db:Session=Depends(get_db),
                  actor=Depends(get_current_superuser)):
    case_or_404(db,repair_id)
    return db.query(RepairEvent).filter(RepairEvent.case_id==repair_id).order_by(
        RepairEvent.revision).limit(250).all()

@router.post("/{repair_id}/transition",response_model=RepairCaseView)
def transition(repair_id:int,payload:RepairTransitionRequest,
               db:Session=Depends(get_db),
               actor=Depends(get_current_superuser)):
    try:
        case=case_or_404(db,repair_id,lock=True)
        already=db.query(RepairEvent).filter(RepairEvent.event_key==payload.event_key).first()
        if already:
            if (already.case_id==case.id and
                already.event_type=="status_change" and
                already.next_status==payload.next_status and
                already.revision==case.revision and
                case.status==payload.next_status):
                return case
            raise HTTPException(409,"Event key already used for a different operation")
        if case.revision!=payload.expected_revision:
            raise HTTPException(409,"Repair case revision conflict")
        previous=case.status
        try:
            updates=state_transition(previous,payload.next_status,
                   existing_quote=case.quote_amount,quote=payload.quote_amount,
                   approval_reference=payload.approval_reference,
                   parts_available=payload.parts_available,qa_passed=payload.qa_passed,
                   existing_qa_passed=case.qa_passed)
        except InvalidRepairTransition as exc:
            raise HTTPException(422,str(exc)) from exc
        for field,value in updates.items():setattr(case,field,value)
        if payload.next_status=="approved":case.approved_by_user_id=actor.id
        case.revision+=1
        event=RepairEvent(case_id=case.id,event_key=payload.event_key,
              event_type="status_change",actor_user_id=actor.id,prior_status=previous,
              next_status=case.status,revision=case.revision)
        db.add(event);db.commit();db.refresh(case)
        return case
    except HTTPException:
        db.rollback()
        raise


@router.post("/{repair_id}/assign",response_model=RepairCaseView)
def assign_technician(repair_id:int,payload:RepairAssignmentRequest,
                      db:Session=Depends(get_db),
                      actor=Depends(get_current_superuser)):
    """Superadmin assignment; role-verified, idempotent, and never notifies anyone."""
    try:
        case=case_or_404(db,repair_id,lock=True)
        old=db.query(RepairEvent).filter(RepairEvent.event_key==payload.event_key).first()
        if old:
            if (old.case_id==case.id and old.event_type=="assignment" and
                old.revision==case.revision and
                case.technician_id==payload.technician_id):
                return case
            raise HTTPException(409,"Event key already used")
        if case.revision!=payload.expected_revision:
            raise HTTPException(409,"Repair case revision conflict")
        if case.status in ("delivered","cancelled"):
            raise HTTPException(422,"Closed repair cannot be reassigned")
        tech=db.query(User).filter(User.id==payload.technician_id,
                                   User.is_active.is_(True)).first()
        role_name=(tech.role.name.strip().lower() if tech and tech.role else "")
        if role_name not in {"tecnico","técnico","technician"}:
            raise HTTPException(422,"Active technician role required")
        if not user_has_location_access(db,tech,case.location_id,"can_edit"):
            raise HTTPException(422,"Technician lacks edit access to case location")
        case.technician_id=tech.id
        case.revision+=1
        db.add(RepairEvent(case_id=case.id,event_key=payload.event_key,
              event_type="assignment",actor_user_id=actor.id,
              prior_status=case.status,next_status=case.status,
              revision=case.revision))
        db.commit();db.refresh(case)
        return case
    except HTTPException:
        db.rollback()
        raise
