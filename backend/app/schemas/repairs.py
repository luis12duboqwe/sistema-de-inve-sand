"""Strict, PII-free repair API payloads. Never send bank details or IMEI."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

Stage=Literal["received","diagnosing","awaiting_approval","approved",
              "awaiting_parts","repairing","quality_check","ready",
              "delivered","cancelled"]
Issue=Literal["screen","battery","charging","software","camera",
              "water_damage","micro_soldering","other"]
class CreateRepairCase(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    intake_key:str=Field(min_length=12,max_length=64,pattern=r"^[a-z0-9-]{12,64}$")
    location_id:int=Field(gt=0)
    device_model:str=Field(min_length=3,max_length=100,pattern=r"^[\w .+\-/()]{3,100}$")
    issue_category:Issue

class RepairCaseView(BaseModel):
    model_config=ConfigDict(from_attributes=True,extra="forbid")
    id:int
    external_reference:str
    location_id:int
    device_model:str
    issue_category:str
    status:str
    technician_id:int|None
    quote_amount:Decimal|None
    quote_approved:bool
    qa_passed:bool
    revision:int
    created_at:datetime

class RepairTransitionRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    expected_revision:int=Field(ge=0)
    next_status:Stage
    event_key:str=Field(min_length=12,max_length=64,pattern=r"^[a-z0-9-]{12,64}$")
    quote_amount:Decimal|None=None
    approval_reference:str|None=Field(default=None,min_length=12,max_length=64,
                                      pattern=r"^[A-Z0-9-]{12,64}$")
    parts_available:bool|None=None
    qa_passed:bool|None=None

class RepairAssignmentRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    expected_revision:int=Field(ge=0)
    technician_id:int=Field(gt=0)
    event_key:str=Field(min_length=12,max_length=64,pattern=r"^[a-z0-9-]{12,64}$")

class RepairEventView(BaseModel):
    model_config=ConfigDict(from_attributes=True,extra="forbid")
    event_type:str
    prior_status:str
    next_status:str
    revision:int
    at:datetime
