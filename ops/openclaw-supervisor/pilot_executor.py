#!/usr/bin/env python3
"""SoftMobile prelaunch executor: internal safe actions, never customer-facing.

Inputs are the sanitized supervisor and director artifacts. Dispatch uses a
fixed allowlist and fixed commands. Only local operator queue, observations
and sandbox test results are written. No Chatwoot, WAHA, Meta Ads, GitHub or
inventory write credentials are used.
"""
from __future__ import annotations
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from director import Reject, verify_snapshot, SALES_TASK_IDS
from supervisor import OUT, save

STORE=OUT/"operator.sqlite3"
LOCK=OUT/"operator.lock"
MAX_TASKS=40
MAX_AGE=5400
ALLOWED={
    "ventas_respuestas", "ventas_seguimiento", "ventas_despliegue",
    "ventas_simulaciones","ventas_calidad_conversacional","ventas_autofix_review",
    "ventas_catalogo_calidad","ventas_dialogos_profundos",
    "finanzas_no_conciliadas", "inventario_sin_stock",
    "inventario_transferencias", "operaciones_fotos",
    "operaciones_reparaciones", "operaciones_empleados",
    "calidad_convergencia", "calidad_replay_aislado",
    "infraestructura_waha_piloto", "infraestructura_servicios",
    "infraestructura_recursos", "publicidad_sin_fuente", "desarrollo_pr"
}
NO_AUTO_ACTION={"ventas_seguimiento","ventas_despliegue",
                "operaciones_reparaciones","operaciones_empleados",
                "publicidad_sin_fuente"}
SQL=r"""
BEGIN TRANSACTION READ ONLY;
SELECT 'SM_EXECUTOR_INV=' || json_build_object(
 'negative_stock',(SELECT count(*) FROM stock WHERE
      cantidad_disponible<0 OR cantidad_reservada<0 OR cantidad_defectuosa<0),
 'out_of_stock_products',(SELECT count(*) FROM products p WHERE p.activo=true
    AND NOT EXISTS(SELECT 1 FROM stock s WHERE s.product_id=p.id
    AND s.cantidad_disponible>0)),
 'completed_orders',(SELECT count(*) FROM orders WHERE completed_at IS NOT NULL),
 'validated_orders',(SELECT count(*) FROM orders WHERE validada_at IS NOT NULL),
 'orders_by_state',(SELECT coalesce(json_object_agg(estado,n),'{}'::json) FROM
    (SELECT coalesce(estado,'unknown') estado,count(*) n
    FROM orders GROUP BY 1) x),
 'transfers_by_state',(SELECT coalesce(json_object_agg(estado,n),'{}'::json) FROM
    (SELECT coalesce(estado,'unknown') estado,count(*) n
    FROM stock_transfers GROUP BY 1) x)
)::text;
COMMIT;
"""

def utc():
    return datetime.now(timezone.utc).isoformat()

def load_inputs(out=OUT,now=None):
    """Fail closed against stale, incomplete, mismatched, externally enabled runs."""
    sup=json.loads((out/"latest.json").read_text())
    director=json.loads((out/"DIRECTOR.json").read_text())
    verify_snapshot(sup,now=now)
    if (director.get("mode")!="proposals_only" or
        director.get("production_changed") is not False or
        director.get("public_messages_sent")!=0 or
        director.get("source_utc")!=sup["captured_utc"] or
        director.get("schema_version")!=1):
        raise Reject("stale/incompatible director or attempted public action")
    tasks=director.get("tasks")
    if not isinstance(tasks,list) or len(tasks)>MAX_TASKS:
        raise Reject("unsafe task list")
    if director.get("scope") not in (None,"sales_only"):
        raise Reject("unknown operating scope")
    seen=set()
    for task in tasks:
        if (not isinstance(task,dict) or task.get("id") not in ALLOWED or
            (director.get("scope")=="sales_only" and task.get("id") not in SALES_TASK_IDS) or
            task.get("id") in seen or
            task.get("status") not in ("review","blocked") or
            task.get("requires_approval") is not True or
            task.get("automatic_external_actions")!=0 or
            task.get("owner")!="humano" or
            task.get("area") not in director.get("specialists",{})):
            raise Reject("unapproved/unknown task")
        seen.add(task["id"])
    gates=sup.get("release_gates",{})
    if gates.get("public_messaging_ready") is not False:
        raise Reject("public messaging gate unexpectedly open")
    return sup,director

def read_inventory():
    p=subprocess.run(["runuser","-u","postgres","--","psql","-X","-At",
                     "-v","ON_ERROR_STOP=1","-d","inventory_db"],
                     input=SQL,text=True,capture_output=True,timeout=18,check=False)
    if p.returncode:
        # Static diagnostic only (no SQL output or credentials in the report).
        if "Permission denied" in p.stderr:
            raise Reject("inventory connection permission_denied")
        if "could not connect" in p.stderr:
            raise Reject("inventory postgres_socket_unavailable")
        if "NoNewPrivileges" in p.stderr or "Unable to change UID" in p.stderr:
            raise Reject("inventory credential_switch_restricted")
        raise Reject("read-only inventory check failed returncode "+str(p.returncode))
    lines=[x.removeprefix("SM_EXECUTOR_INV=") for x in p.stdout.splitlines()
           if x.startswith("SM_EXECUTOR_INV=")]
    if len(lines)!=1:
        raise Reject("inventory response missing/duplicated")
    data=json.loads(lines[0])
    for key in ("negative_stock","out_of_stock_products","completed_orders","validated_orders"):
        if type(data.get(key)) is not int or data[key]<0:
            raise Reject("inventory check invalid")
    for key in ("orders_by_state","transfers_by_state"):
        values=data.get(key)
        if not isinstance(values,dict) or any(
            not isinstance(k,str) or type(v) is not int or v<0
            for k,v in values.items()):
            raise Reject("inventory status data invalid")
    return data

def read_photo(ids):
    """Check IDs in the existing pilot SQLite; no photos, message text or PII."""
    if type(ids) is not list or any(type(n) is not int or n<1 for n in ids):
        raise Reject("unsafe photo IDs")
    result=[]
    path="file:/opt/softmobile-waha-test/staff-bridge/requests.sqlite3?mode=ro"
    with sqlite3.connect(path,uri=True,timeout=4) as db:
        db.execute("PRAGMA query_only=ON")
        for n in ids[:50]:
            rec=db.execute("SELECT status FROM requests WHERE id=?",(n,)).fetchone()
            result.append({"request_id":n,
                           "status":str(rec[0])[:60] if rec else "missing"})
    return result

def containers():
    """Fixed names; no dynamic shell input and no restart."""
    names=["softmobile-waha-test-waha-1","softmobile-waha-test-redis-1"]
    statuses={}
    for name in names:
        p=subprocess.run(["docker","inspect","--format","{{.State.Status}}",name],
                         capture_output=True,text=True,timeout=6,check=False)
        statuses[name]=p.stdout.strip() if p.returncode==0 else "missing"
    return statuses

def code_tests():
    """Run a strictly bounded, local no-network Python unit suite."""
    p=subprocess.run(["/usr/bin/python3","-m","unittest","discover","-q",
                      "-p","test_*.py"],cwd="/opt/openclaw-lab/supervisor",
                     env={"PYTHONDONTWRITEBYTECODE":"1","PATH":"/usr/bin:/bin"},
                     capture_output=True,text=True,timeout=15,check=False)
    return {"passed":p.returncode==0,"return_code":p.returncode,
            "tests_verified":int(__import__("re").search(r"Ran (\d+) tests",
                        p.stderr or p.stdout).group(1))
                        if __import__("re").search(r"Ran (\d+) tests",p.stderr or p.stdout) else None}

def safe_action(task,sup,cache):
    """Internal action: verify a bounded source and create an approval task."""
    tid=task["id"]
    if task["status"]=="blocked" or tid in NO_AUTO_ACTION:
        return "blocked",{"reason":"manual_approval_or_missing_integration"}
    if tid=="ventas_simulaciones":
        evidence=task.get("evidence") or {}
        total=evidence.get("scenarios")
        passed=evidence.get("passed")
        failed=evidence.get("failed")
        if (any(type(x) is not int for x in (total,passed,failed)) or
            not 0<total<=1000 or not 0<=passed<=total or failed!=total-passed or
            evidence.get("synthetic_only") is not True):
            raise Reject("unsafe synthetic sales results")
        return ("checked_needs_review" if failed==0 else "needs_attention"),{
            "synthetic_sales_scenarios":total,"passed":passed,"failed":failed,
            "verified_real_sales":0}
    if tid=="ventas_dialogos_profundos":
        e=task.get("evidence") or {}
        expected=("scenarios","buyer_messages","checks","passed","failed")
        if (not isinstance(e,dict) or
            any(type(e.get(k)) is not int for k in expected) or
            e["scenarios"]!=10 or e["buyer_messages"]!=150 or e["checks"]!=32 or
            not 0<=e["passed"]<=32 or e["failed"]!=32-e["passed"] or
            e.get("synthetic_only") is not True or
            e.get("candidate_deployed") is not False or
            e.get("public_messages_sent")!=0):
            raise Reject("unsafe deep seller quality evidence")
        return "awaiting_qa",{
          "buyer_dialogues":10,"buyer_messages":150,
          "quality_checks":32,"checks_passed":e["passed"],
          "checks_failed":e["failed"],"real_sales":0,
          "public_messages_sent":0,"deploy_authorized":False}
    if tid=="ventas_catalogo_calidad":
        v=task.get("evidence") or {}
        required=("active_products","stocked_active_products",
                  "stocked_fully_specified","active_without_stock",
                  "active_price_below_cost")
        if (not isinstance(v,dict) or
            any(type(v.get(k)) is not int or v[k]<0 for k in required) or
            v["active_products"]<v["stocked_active_products"] or
            v["stocked_active_products"]<v["stocked_fully_specified"] or
            v["active_without_stock"]!=v["active_products"]-v["stocked_active_products"] or
            v.get("public_quote_authorized") is not False or
            v.get("fresh_partner_quote_available") is not False):
            raise Reject("unsafe catalog quality proposal")
        return "awaiting_human",{
           "active_products":v["active_products"],
           "stocked":v["stocked_active_products"],
           "fully_specified":v["stocked_fully_specified"],
           "pricing_below_cost_requires_review":v["active_price_below_cost"],
           "public_quote_authorized":False,
           "fresh_partner_quote_available":False,
           "customer_messages_sent":0}
    if tid=="ventas_autofix_review":
        evidence=task.get("evidence") or {}
        if (not isinstance(evidence,dict) or
            evidence.get("dialogues_passed")!=72 or
            evidence.get("rotating_passed")!=6 or
            evidence.get("adversarial_passed")!=11 or
            type(evidence.get("unit_tests_passed")) is not int or
            evidence["unit_tests_passed"]<68 or
            evidence.get("reference_only_agent_firewall_verified") is not True or
            evidence.get("candidate_deployed") is not False or
            evidence.get("public_messages_sent")!=0 or
            evidence.get("requires_human_review") is not True or
            any(not isinstance(evidence.get(k),str) or
                not re.fullmatch(r"[0-9a-f]{64}",evidence[k])
                for k in ("source_sha256","candidate_sha256"))):
            raise Reject("unsafe automated sales candidate review")
        return "awaiting_qa",{
            "candidate_sha256":evidence["candidate_sha256"],
            "source_sha256":evidence["source_sha256"],
            "verified_synthetic_reply_cases":72,
            "rotating_challenges_passed":6,
            "adversarial_cases_passed":11,
            "unit_tests_passed":evidence["unit_tests_passed"],
            "reference_only_agent_firewall_verified":True,
            "code_deployed":False,"public_messages_sent":0,
            "review_required":True}
    if tid=="ventas_calidad_conversacional":
        evidence=task.get("evidence") or {}
        tested,passed,failed=(evidence.get(k) for k in ("scenarios","passed","failed"))
        if (any(type(x) is not int for x in (tested,passed,failed)) or
            tested!=72 or not 0<=passed<=tested or failed!=tested-passed or
            evidence.get("synthetic_only") is not True or
            evidence.get("verified_real_sales")!=0 or
            not isinstance(evidence.get("ruby_source_sha256"),str) or
            len(evidence["ruby_source_sha256"])!=64):
            raise Reject("invalid reply-quality evidence")
        return ("awaiting_qa" if failed else "checked_needs_review"),{
          "buyer_reply_scenarios":tested,"passed":passed,"failed":failed,
          "real_sales_verified":0,
          "quality_gate":"synthetic_sales_dialogues_only"}
    if tid=="ventas_respuestas":
        ids=task["evidence"].get("conversation_ids",[])
        if not isinstance(ids,list) or any(type(x) is not int or x<1 for x in ids):
            raise Reject("unsafe conversation IDs")
        confirmed=set(sup.get("chatwoot",{}).get("queues",{}).get("unanswered",[]))
        if not set(ids).issubset(confirmed):
            raise Reject("queue not present in live supervisor")
        return "awaiting_human",{"pilot_conversation_ids":sorted(set(ids)),
                                  "verified_in_supervisor":True}
    if tid=="operaciones_fotos":
        ids=task["evidence"].get("request_ids",[])
        checked=read_photo(ids)
        return "awaiting_human",{"pilot_photo_checks":checked}
    if tid in ("finanzas_no_conciliadas","inventario_sin_stock","inventario_transferencias"):
        if "inventory" not in cache:
            cache["inventory"]=read_inventory()
        result=cache["inventory"]
        fields={
          "finanzas_no_conciliadas":("completed_orders","validated_orders","orders_by_state"),
          "inventario_sin_stock":("out_of_stock_products","negative_stock"),
          "inventario_transferencias":("transfers_by_state",)}
        return "checked_needs_review",{key:result[key] for key in fields[tid]}
    if tid=="infraestructura_waha_piloto":
        return "checked_needs_review",{"pilot_container_states":containers()}
    if tid=="calidad_replay_aislado":
        qa=sup.get("quality",{})
        return "awaiting_qa",{"local_tests_passed":qa.get("all_local_tests_passed") is True,
                             "independent_convergence":qa.get("independent_convergence") is True}
    if tid=="calidad_convergencia":
        return "awaiting_qa",{"independent_convergence":
                              sup.get("quality",{}).get("independent_convergence") is True}
    if tid=="desarrollo_pr":
        if "tests" not in cache:
            cache["tests"]=code_tests()
        info=cache["tests"]
        return ("checked_needs_review" if info["passed"] else "needs_attention"),info
    if tid.startswith("infraestructura_"):
        h=sup.get("health",{})
        return "checked_needs_review",{"containers_running":h.get("all_containers_running"),
              "memory_available_percent":h.get("memory_available_percent"),
              "disk_free_percent":h.get("disk_free_percent")}
    raise Reject("task not in internal executor allowlist")

def init_db(con):
    con.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        evidence_digest TEXT NOT NULL,
        state TEXT NOT NULL,
        first_seen_utc TEXT NOT NULL,
        last_seen_utc TEXT NOT NULL,
        last_checked_utc TEXT NOT NULL,
        checks INTEGER NOT NULL CHECK (checks>=1),
        details_json TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_utc TEXT NOT NULL,
        source_utc TEXT NOT NULL,
        inspected INTEGER NOT NULL,
        failures INTEGER NOT NULL
    )""")

def execute(sup,director,con,now=None):
    """Atomic idempotent state transition; no writes outside local operator DB."""
    now=now or utc()
    cache={}
    results=[]
    seen=set()
    for t in director["tasks"]:
        tid=t["id"]
        digest=hashlib.sha256(json.dumps(t.get("evidence") or {},
                    ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        try:
            state,detail=safe_action(t,sup,cache)
        except (Reject,OSError,ValueError,TypeError,sqlite3.Error,
                subprocess.TimeoutExpired,KeyError) as exc:
            # Only local static error codes; never leak database errors, texts or PII.
            allowed_reason=str(exc)[:90] if isinstance(exc,Reject) else "unavailable"
            state,detail="needs_attention",{"reason":"internal_validation_failed",
                                           "error_type":type(exc).__name__,
                                           "error_code":allowed_reason}
        prior=con.execute("SELECT checks,first_seen_utc FROM tasks WHERE id=?",
                          (tid,)).fetchone()
        checks=prior[0]+1 if prior else 1
        first=prior[1] if prior else now
        con.execute("""INSERT INTO tasks (id,evidence_digest,state,first_seen_utc,
          last_seen_utc,last_checked_utc,checks,details_json)
          VALUES (?,?,?,?,?,?,?,?)
          ON CONFLICT(id) DO UPDATE SET evidence_digest=excluded.evidence_digest,
          state=excluded.state,last_seen_utc=excluded.last_seen_utc,
          last_checked_utc=excluded.last_checked_utc,checks=excluded.checks,
          details_json=excluded.details_json""",
          (tid,digest,state,first,now,now,checks,
           json.dumps(detail,ensure_ascii=False,sort_keys=True)))
        results.append({"id":tid,"state":state,"priority":t["priority"],
                        "checks":checks,"details":detail,"requires_human_approval":True})
        seen.add(tid)
    # Non-present tasks are NOT marked completed; they may simply be out of scope.
    failures=sum(t["state"]=="needs_attention" for t in results)
    con.execute("""INSERT INTO cycles(started_utc,source_utc,inspected,failures)
       VALUES (?,?,?,?)""",(now,director["source_utc"],len(results),failures))
    con.execute("""DELETE FROM cycles WHERE id NOT IN
       (SELECT id FROM cycles ORDER BY id DESC LIMIT 150)""")
    summary={}
    for t in results: summary[t["state"]]=summary.get(t["state"],0)+1
    return {"schema_version":1,"mode":"internal_actions_only","at":now,
            "source_utc":director["source_utc"],"checked":len(results),
            "states":summary,"tasks":results,"public_messages_sent":0,
            "paid_actions":0,"public_messaging_enabled":False,
            "production_changed":False,"external_actions":0,
            "approval_required_for_all_external_actions":True,
            "failures":failures}

def markdown(out):
    lines=["# SoftMobile | Ejecutor interno previo a lanzamiento",
      "Acciones ejecutadas: validaciones SOLO LECTURA y asignación de tareas locales.",
      "UTC: "+out["at"],"Fuente UTC: "+out["source_utc"],
      "Tareas comprobadas: "+str(out["checked"]),
      "Estados: "+json.dumps(out["states"],ensure_ascii=False,sort_keys=True),
      "Envíos al público: 0 | Compras: 0 | Despliegues: 0 | Meta Ads: sin cambios.",
      "Cualquier acción externa requiere aprobación y pruebas del piloto.",""]
    for t in out["tasks"]:
        lines.append("- "+t["id"]+": "+t["state"]+
                     " ("+str(t["checks"])+" verificaciones)")
    lines.append("\nLos IDs del buzón piloto y fotos quedan solo en OPERATOR.json.")
    return "\n".join(lines)+"\n"

def main():
    fd=os.open(LOCK,os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            sup,director=load_inputs()
        except (Reject,OSError,ValueError,TypeError,KeyError) as exc:
            print(json.dumps({"status":"rejected","reason":type(exc).__name__}))
            return 2
        with sqlite3.connect(STORE,timeout=5) as con:
            con.execute("PRAGMA busy_timeout=5000")
            init_db(con)
            out=execute(sup,director,con)
        os.chmod(STORE,0o600)
        save(OUT/"OPERATOR.json",json.dumps(out,indent=2,ensure_ascii=False)+"\n")
        save(OUT/"OPERATOR.md",markdown(out))
        print(json.dumps({"status":"ok","checked":out["checked"],
             "states":out["states"],"failures":out["failures"],
             "public_messages_sent":0},ensure_ascii=False))
        return 0 if out["failures"]==0 else 2
    except BlockingIOError:
        print('operator_busy')
        return 0
    finally:
        os.close(fd)

if __name__=="__main__":
    raise SystemExit(main())
