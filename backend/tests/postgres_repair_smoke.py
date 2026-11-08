#!/usr/bin/env python3
"""Manual NO-NETWORK ephemeral PostgreSQL smoke for the repair API.

Requires SM_TEST_PG_SOCKET pointing to a directory /tmp/sm-repairs-pg-*.
NEVER executes SQL against inventory_db or any externally reachable database.
Run twice: 'bootstrap' before applying reviewed DDL; 'verify' after.
"""
import os
from pathlib import Path
import sys
import json
import argparse
from urllib.parse import quote

parser=argparse.ArgumentParser()
parser.add_argument("phase",choices=("bootstrap","verify"))
args=parser.parse_args()
socket=os.getenv("SM_TEST_PG_SOCKET","")
if (not socket.startswith("/tmp/sm-repairs-pg-") or
    "/" in socket[len("/tmp/sm-repairs-pg-"):] or
    not Path(socket).is_dir() or
    os.getenv("ENVIRONMENT")!="testing"):
    raise SystemExit("REFUSED: not a private ephemeral PostgreSQL socket")
os.environ["DATABASE_URL"]=(
    "postgresql+psycopg2://postgres@/postgres?host="+quote(socket,safe="/"))
os.environ["DEBUG"]="true"
os.environ["SENTRY_DISABLED"]="true"
sys.path.insert(0,"/var/www/inventario/backend")
import app.models,app.routers,app.schemas,app.services
root=Path(__file__).resolve().parents[1]
for pkg,sub in ((app.models,"models"),(app.routers,"routers"),
                (app.schemas,"schemas"),(app.services,"services")):
    pkg.__path__.insert(0,str(root/"app"/sub))
from app.database import Base
from app.models.rbac import Role,User
from app.models.location import Location
from app.models.control import UserLocationAccess
from sqlalchemy import create_engine,inspect
from sqlalchemy.orm import Session,sessionmaker
engine=create_engine(os.environ["DATABASE_URL"])
def initialize():
    # Explicit, ONLY temporary fixture tables. Not the actual repair schema.
    Base.metadata.create_all(engine,tables=[
      Role.__table__,Location.__table__,User.__table__,
      UserLocationAccess.__table__])
    with Session(engine) as db:
        db.add_all([
           Role(id=1,name="Repair pg admin",is_system_role=False),
           Role(id=2,name="Técnico",is_system_role=False)])
        db.flush()
        db.add(User(id=1,username="pg_admin_1",hashed_password="fake",
                    role_id=1,is_active=True,is_superuser=True))
        db.add(User(id=2,username="pg_technician_2",hashed_password="fake",
                    role_id=2,is_active=True,is_superuser=False))
        db.add(Location(id=1,nombre="Local ficticio",nombre_normalized="local ficticio",
                        nombre_key_hash="2"*64,tipo="Taller",activo=True))
        db.add(UserLocationAccess(user_id=2,location_id=1,
                                  can_view=True,can_edit=True))
        db.commit()
    return "bootstrap_ok"

def verify():
    from app.services.repair_schema_guard import require_preinstalled_repair_schema
    require_preinstalled_repair_schema(engine)
    from app.routers.repairs import router
    from app.database import get_db
    from app.auth import get_current_superuser
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    class Admin:
        id=1
        is_superuser=True
        is_active=True
    app=FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_superuser]=lambda:Admin()
    def db_session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db]=db_session
    os.environ["SOFTMOBILE_REPAIRS_ENABLED"]="true"
    with TestClient(app) as client:
        result=client.post("/api/repairs",json={
          "location_id":1,"device_model":"iPhone 13 ficticio",
          "issue_category":"screen","intake_key":"pg-test-intake-0001"})
        assert result.status_code==201,result.text
        case=result.json()
        cid=case["id"]
        duplicate=client.post("/api/repairs",json={
          "location_id":1,"device_model":"iPhone 13 ficticio",
          "issue_category":"screen","intake_key":"pg-test-intake-0001"})
        assert duplicate.status_code==201 and duplicate.json()["id"]==cid
        different=client.post("/api/repairs",json={
          "location_id":1,"device_model":"iPhone 12 distinto",
          "issue_category":"screen","intake_key":"pg-test-intake-0001"})
        assert different.status_code==409
        assignment=client.post(f"/api/repairs/{cid}/assign",
              json={"expected_revision":case["revision"],
                    "technician_id":2,"event_key":"pg-test-assign-0001"})
        assert assignment.status_code==200,assignment.text
        case=assignment.json()
        steps=[
          ("diagnosing",{}),
          ("awaiting_approval",{"quote_amount":"1250.00"}),
          ("approved",{"approval_reference":"APPROVED-TEST-1234"}),
          ("repairing",{"parts_available":True}),
          ("quality_check",{}),
          ("ready",{"qa_passed":True}),
          ("delivered",{})]
        for i,(status,details) in enumerate(steps):
            response=client.post(f"/api/repairs/{cid}/transition",
               json={"next_status":status,"expected_revision":case["revision"],
                     "event_key":f"pg-test-transition-{i:04d}",**details})
            assert response.status_code==200,(status,response.text)
            case=response.json()
            assert case["status"]==status
        events=client.get(f"/api/repairs/{cid}/events")
        assert events.status_code==200,events.text
        assert len(events.json())==len(steps)+1
        assert case["revision"]==8
        assert case["qa_passed"] is True
        assert case["quote_approved"] is True
        assert "customer_phone" not in case and "imei" not in case
        assert client.get("/api/repairs/overview").json()["by_status"]=={"delivered":1}
        duplicate=client.post(f"/api/repairs/{cid}/transition",
              json={"next_status":"diagnosing","expected_revision":1,
                    "event_key":"pg-test-transition-0000"})
        assert duplicate.status_code==409,duplicate.text
    return {"status":"ok","postgresql":True,"cases":1,
      "events":8,"real_repairs":0,"public_messages_sent":0,
      "payments_made":0,"real_inventory_changed":False}
try:
    print(json.dumps(initialize() if args.phase=="bootstrap" else verify()))
finally:
    engine.dispose()
