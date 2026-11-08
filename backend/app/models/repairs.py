"""Internal repair case tables, isolated until feature flag & migration approval."""
from sqlalchemy import (Column,Integer,String,DateTime,ForeignKey,Boolean,
                        Numeric,UniqueConstraint,Index)
from sqlalchemy.sql import func
from app.database import Base

class RepairCase(Base):
    __tablename__="repair_cases"
    id=Column(Integer,primary_key=True)
    external_reference=Column(String(64),unique=True,nullable=False,index=True)
    location_id=Column(Integer,ForeignKey("locations.id",ondelete="RESTRICT"),
                       nullable=False,index=True)
    device_model=Column(String(100),nullable=False)
    issue_category=Column(String(32),nullable=False,index=True)
    status=Column(String(32),nullable=False,default="received",index=True)
    technician_id=Column(Integer,ForeignKey("users.id",ondelete="SET NULL"),
                         nullable=True,index=True)
    quote_amount=Column(Numeric(12,2),nullable=True)
    approval_reference_digest=Column(String(64),nullable=True)
    quote_approved=Column(Boolean,nullable=False,default=False)
    approved_by_user_id=Column(Integer,ForeignKey("users.id",ondelete="SET NULL"),
                               nullable=True)
    parts_available=Column(Boolean,nullable=True)
    qa_passed=Column(Boolean,nullable=False,default=False)
    revision=Column(Integer,nullable=False,default=0)
    created_at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at=Column(DateTime(timezone=True),server_default=func.now(),
                      onupdate=func.now(),nullable=False)
    __table_args__=(Index("idx_repair_cases_location_status","location_id","status"),)

class RepairEvent(Base):
    __tablename__="repair_events"
    id=Column(Integer,primary_key=True)
    case_id=Column(Integer,ForeignKey("repair_cases.id",ondelete="RESTRICT"),
                   nullable=False,index=True)
    event_key=Column(String(64),nullable=False,unique=True)
    event_type=Column(String(32),nullable=False,default="status_change")
    actor_user_id=Column(Integer,ForeignKey("users.id",ondelete="RESTRICT"),nullable=False)
    prior_status=Column(String(32),nullable=False)
    next_status=Column(String(32),nullable=False)
    revision=Column(Integer,nullable=False)
    at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    __table_args__=(UniqueConstraint("case_id","revision",name="uq_repair_event_revision"),)
