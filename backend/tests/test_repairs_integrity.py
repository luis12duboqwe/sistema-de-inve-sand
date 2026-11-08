"""Feature-gated repair API acceptance in isolated in-memory SQLite only.

No import of app.main, no production env, no network and no worker sends.
"""
import os
os.environ["ENVIRONMENT"]="testing"
os.environ["DEBUG"]="true"
os.environ["DATABASE_URL"]="sqlite:////tmp/softmobile-repair-candidate-unconnected.db"
os.environ["SENTRY_DISABLED"]="true"
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base,get_db
import app.models,app.routers,app.schemas,app.services
ROOT=Path(__file__).resolve().parents[1]
for package,relative in (
    (app.models,"models"),(app.routers,"routers"),(app.schemas,"schemas"),
    (app.services,"services")):
    package.__path__.insert(0,str(ROOT/"app"/relative))
from app.models.location import Location
from app.models.rbac import User,Role
from app.models.repairs import RepairCase,RepairEvent
from app.routers.repairs import router
from app.auth import get_current_superuser

class Actor:
    id=1
    is_superuser=True
    is_active=True

class RepairsAPITests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite://",connect_args={"check_same_thread":False},
                                  poolclass=StaticPool)
        Base.metadata.create_all(self.engine,tables=[
            Role.__table__,Location.__table__,User.__table__,
            RepairCase.__table__,RepairEvent.__table__])
        Session=sessionmaker(bind=self.engine)
        with Session() as db:
            db.add(Role(id=1,name="Repair test admin",is_system_role=False))
            db.add(Role(id=2,name="Tecnico",is_system_role=False))
            db.flush()
            db.add(User(id=1,username="repair_test_user",hashed_password="not_real",
                        role_id=1,is_active=True,is_superuser=True))
            db.add(User(id=2,username="repair_test_technician",hashed_password="not_real",
                        role_id=2,is_active=True,is_superuser=False))
            db.add(Location(id=1,nombre="Taller prueba",nombre_normalized="taller prueba",
                    nombre_key_hash="x"*64,tipo="Taller",activo=True))
            db.commit()
        self.app=FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_current_superuser]=lambda:Actor()
        def db_override():
            with Session() as db:
                yield db
        self.app.dependency_overrides[get_db]=db_override
        self.client=TestClient(self.app)
        self.flags=patch.dict(os.environ,{"SOFTMOBILE_REPAIRS_ENABLED":"true"})
        self.flags.start()
    def tearDown(self):
        self.flags.stop()
        self.client.close()
        self.engine.dispose()
    def create(self):
        res=self.client.post("/api/repairs",json={
            "location_id":1,"device_model":"Samsung S23 Ultra","issue_category":"screen"})
        self.assertEqual(res.status_code,201,res.text)
        return res.json()
    def transition(self,case,status,rev,event,**kw):
        return self.client.post(f"/api/repairs/{case['id']}/transition",
           json={"next_status":status,"expected_revision":rev,"event_key":event,**kw})
    def test_disabled_by_default(self):
        with patch.dict(os.environ,{"SOFTMOBILE_REPAIRS_ENABLED":"false"}):
            r=self.client.post("/api/repairs",json={
                "location_id":1,"device_model":"iPhone 14 Pro","issue_category":"battery"})
        self.assertEqual(r.status_code,503)
    def test_no_auth_is_forbidden(self):
        self.app.dependency_overrides.clear()
        r=self.client.get("/api/repairs")
        self.assertIn(r.status_code,(401,403))
    def test_create_and_anonymous_reference(self):
        case=self.create()
        self.assertEqual(case["status"],"received")
        self.assertTrue(case["external_reference"].startswith("RPR-"))
        self.assertNotIn("customer_phone",case)
        self.assertNotIn("imei",case)
        self.assertEqual(self.client.get("/api/repairs/overview").json()["records"],1)
        self.assertEqual(len(self.client.get("/api/repairs").json()),1)
    def test_phone_and_imei_fields_are_rejected(self):
        for extra in ("customer_phone","imei","bank_account"):
            body={"location_id":1,"device_model":"iPhone 14 Pro",
                  "issue_category":"screen",extra:"secret"}
            self.assertEqual(self.client.post("/api/repairs",json=body).status_code,422)
    def test_only_active_locations(self):
        r=self.client.post("/api/repairs",json={
            "location_id":999,"device_model":"iPhone 14 Pro","issue_category":"screen"})
        self.assertEqual(r.status_code,422)
    def test_full_manual_approval_and_qa(self):
        case=self.create()
        steps=[
          ("diagnosing",{}),
          ("awaiting_approval",{"quote_amount":"1250.00"}),
          ("approved",{"approval_reference":"APPROVED-ABCD123456"}),
          ("repairing",{"parts_available":True}),
          ("quality_check",{}),
          ("ready",{"qa_passed":True}),
          ("delivered",{})]
        for i,(status,params) in enumerate(steps):
            r=self.transition(case,status,i,f"event-repair-{i:04d}",**params)
            self.assertEqual(r.status_code,200,r.text)
            case=r.json()
            self.assertEqual(case["revision"],i+1)
            self.assertEqual(case["status"],status)
        ev=self.client.get(f"/api/repairs/{case['id']}/events")
        self.assertEqual(ev.status_code,200)
        self.assertEqual(len(ev.json()),len(steps))
        self.assertEqual(self.client.get("/api/repairs/overview").json()["by_status"],{"delivered":1})
    def test_cannot_approve_without_reference(self):
        case=self.create()
        x=self.transition(case,"diagnosing",0,"event-repair-0001").json()
        x=self.transition(x,"awaiting_approval",1,"event-repair-0002",quote_amount="500").json()
        r=self.transition(x,"approved",2,"event-repair-0003")
        self.assertEqual(r.status_code,422)
    def test_stale_revision_blocks(self):
        case=self.create()
        r=self.transition(case,"diagnosing",1,"event-repair-1001")
        self.assertEqual(r.status_code,409)
    def test_repeated_event_does_not_repeat_ledger(self):
        case=self.create()
        x=self.transition(case,"diagnosing",0,"event-repair-1002").json()
        again=self.transition(x,"diagnosing",0,"event-repair-1002")
        self.assertEqual(again.status_code,200)
        self.assertEqual(len(self.client.get(f"/api/repairs/{x['id']}/events").json()),1)
        r=self.transition(x,"cancelled",1,"event-repair-1002")
        self.assertEqual(r.status_code,409)
    def test_cannot_skip_qa(self):
        case=self.create()
        r=self.transition(case,"ready",0,"event-repair-1234",qa_passed=True)
        self.assertEqual(r.status_code,422)
    def test_invalid_amount(self):
        case=self.create()
        x=self.transition(case,"diagnosing",0,"event-repair-2001").json()
        r=self.transition(x,"awaiting_approval",1,"event-repair-2002",quote_amount="-100")
        self.assertEqual(r.status_code,422)
    def test_assignment_only_to_active_technician_role(self):
        case=self.create()
        payload={"expected_revision":0,"technician_id":2,
                 "event_key":"event-repair-assign-01"}
        res=self.client.post(f"/api/repairs/{case['id']}/assign",json=payload)
        self.assertEqual(res.status_code,200,res.text)
        assigned=res.json()
        self.assertEqual(assigned["technician_id"],2)
        self.assertEqual(assigned["revision"],1)
        rows=self.client.get(f"/api/repairs/{case['id']}/events").json()
        self.assertEqual(rows[0]["event_type"],"assignment")
        repeated=self.client.post(f"/api/repairs/{case['id']}/assign",json=payload)
        self.assertEqual(repeated.status_code,200)
        self.assertEqual(len(self.client.get(f"/api/repairs/{case['id']}/events").json()),1)
    def test_non_technician_rejected(self):
        case=self.create()
        payload={"expected_revision":0,"technician_id":1,
                 "event_key":"event-repair-assign-02"}
        res=self.client.post(f"/api/repairs/{case['id']}/assign",json=payload)
        self.assertEqual(res.status_code,422)
    def test_assignment_cannot_use_stale_revision(self):
        case=self.create()
        payload={"expected_revision":5,"technician_id":2,
                 "event_key":"event-repair-assign-03"}
        res=self.client.post(f"/api/repairs/{case['id']}/assign",json=payload)
        self.assertEqual(res.status_code,409)
    def test_unknown_case_is_not_exposed(self):
        self.assertEqual(self.client.get("/api/repairs/999").status_code,404)
        self.assertEqual(self.client.get("/api/repairs/999/events").status_code,404)

if __name__=="__main__":
    unittest.main()
