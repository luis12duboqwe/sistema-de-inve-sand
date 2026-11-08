#!/usr/bin/env python3
"""Repair workflow lab and integration probe (zero real repair writes)."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json
import subprocess

from supervisor import OUT,save
from repair_workflow import run_synthetic_cases

QUERY=r"""BEGIN TRANSACTION READ ONLY;
SELECT 'SM_REPAIRS_PROBE='||json_build_object(
 'repair_cases_table_exists',EXISTS(
   SELECT 1 FROM information_schema.tables
   WHERE table_schema='public' AND table_name='repair_cases'),
 'repair_events_table_exists',EXISTS(
   SELECT 1 FROM information_schema.tables
   WHERE table_schema='public' AND table_name='repair_events')
)::text;
COMMIT;"""
ROUTE=Path("/var/www/inventario/backend/app/routers/repairs.py")
MODEL=Path("/var/www/inventario/backend/app/models/repairs.py")

def probe():
    p=subprocess.run(["runuser","-u","postgres","--","psql","-X","-At",
                      "-v","ON_ERROR_STOP=1","-d","inventory_db"],
                     input=QUERY,text=True,capture_output=True,timeout=12,check=False)
    if p.returncode:raise RuntimeError("repair source schema check unavailable")
    values=[s[len("SM_REPAIRS_PROBE="):] for s in p.stdout.splitlines()
            if s.startswith("SM_REPAIRS_PROBE=")]
    if len(values)!=1:raise RuntimeError("invalid repair schema response")
    schema=json.loads(values[0])
    if any(type(schema.get(k)) is not bool for k in
       ("repair_cases_table_exists","repair_events_table_exists")):
        raise ValueError("invalid repair schema types")
    # Presence of files and tables is not proof of an operational connection.
    return {"repair_cases_table_exists":schema["repair_cases_table_exists"],
            "repair_events_table_exists":schema["repair_events_table_exists"],
            "backend_repair_router_file_exists":ROUTE.is_file(),
            "backend_repair_model_file_exists":MODEL.is_file(),
            "real_workflow_verified":False}

def analyze(source_utc,observed,simulated=None,now=None):
    if not isinstance(source_utc,str) or len(source_utc)<10:
        raise ValueError("missing cycle reference")
    if any(type(observed.get(k)) is not bool for k in (
        "repair_cases_table_exists","repair_events_table_exists",
        "backend_repair_router_file_exists","backend_repair_model_file_exists",
        "real_workflow_verified")):
        raise ValueError("unverifiable repair source")
    simulated=simulated if simulated is not None else run_synthetic_cases(60)
    if (simulated.get("environment")!="SYNTHETIC_OFFLINE_ONLY" or
        simulated.get("real_repairs")!=0 or simulated.get("public_messages_sent")!=0 or
        simulated.get("payments_initiated")!=0 or
        simulated.get("real_inventory_mutations")!=0 or
        simulated.get("source_connected") is not False or
        simulated.get("cases")!=60 or simulated.get("passed")!=60 or
        simulated.get("failed")!=0):
        raise ValueError("repair lab failed")
    return {
       "schema_version":1,"mode":"repair_simulation_and_source_probe",
       "at":now or datetime.now(timezone.utc).isoformat(),
       "source_utc":source_utc,"offline_domain_cases":60,"offline_domain_passed":60,
       "real_repair_cases_processed":0,
       "repair_workflow_connected":False,
       "source_probe":observed,
       "manual_approval_to_advance_required":True,
       "customer_data_extracted":False,
       "public_messages_sent":0,"real_inventory_mutations":0,
       "financial_actions":0,"production_changed":False}
def markdown(out):
    observed=out["source_probe"]
    return "\n".join([
      "# SoftMobile — Reparaciones: flujo interno en preparación",
      "UTC: "+out["at"],"Referencia: "+out["source_utc"],
      "Ensayos de órdenes ficticias: 60/60 aprobados.",
      "Casos reales tratados: 0. Integración con taller: PENDIENTE.",
      "Modelo del backend encontrado: "+str(observed["backend_repair_model_file_exists"]),
      "Router del backend encontrado: "+str(observed["backend_repair_router_file_exists"]),
      "Tabla de reparaciones encontrada: "+str(observed["repair_cases_table_exists"]),
      "Tabla de historial encontrada: "+str(observed["repair_events_table_exists"]),
      "Los ensayos NO crean empleados, citas, presupuestos reales ni mensajes.",
      "Para operar: integrar modelo, migración, roles, API y control de técnicos.",
      "Nunca activar contactos ni cobros desde este laboratorio.",""
    ])
def main():
    try:
        operator=json.loads((OUT/"OPERATOR.json").read_text())
        director=json.loads((OUT/"DIRECTOR.json").read_text())
        source=operator.get("source_utc")
        if (source!=director.get("source_utc") or
            operator.get("mode")!="internal_actions_only" or
            operator.get("failures")!=0 or
            operator.get("external_actions")!=0 or
            operator.get("public_messages_sent")!=0):
            raise ValueError("unsafe prior stage")
        age=(datetime.now(timezone.utc)-
             datetime.fromisoformat(source.replace("Z","+00:00"))).total_seconds()
        if not 0<=age<=5400:raise ValueError("source stale")
        result=analyze(source,probe())
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.TimeoutExpired):
        print("repair_lab_blocked")
        return 2
    save(OUT/"REPAIRS_LAB.json",json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"REPAIRS_LAB.md",markdown(result))
    print(json.dumps({"status":"offline_cases_passed","cases":60,
         "real_source_connected":False,"public_messages_sent":0},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
