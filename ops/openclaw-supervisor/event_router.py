#!/usr/bin/env python3
"""Prelaunch internal event router for SoftMobile OpenClaw.

Not a WhatsApp webhook: consumes already redacted internal supervisor/director
and operator reports. Emits changed tasks and work items for read-only agents.
No messaging, commerce, advertising, service recovery or code deployment.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import os
import sqlite3
import subprocess

from supervisor import OUT, save
from pilot_executor import load_inputs, Reject, ALLOWED

LEDGER=OUT/"events.sqlite3"
LOCK=OUT/"events.lock"
ROLE_JOB_IDS={
    "ventas":"d70dd8ed-eb9f-451c-9e40-067da8ed3a6c",
    "operaciones":"95463b81-f543-43c2-adbf-60539abae030",
    "ingenieria":"43b90337-7acc-49d2-9dff-7cf58f8377fc"
}
ROLE_ORDER=("ventas","operaciones","ingenieria")
MAX_HISTORY=300
MAX_EVENT_DISPATCHES_PER_DAY=3
ROLE={"ventas":"ventas","inventario":"operaciones","finanzas":"operaciones",
      "operaciones":"operaciones","calidad":"ingenieria",
      "infraestructura":"ingenieria","desarrollo":"ingenieria",
      "publicidad":"ventas"}
PRIORITY={"alta":0,"media":1,"baja":2}

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,
                          separators=(",",":")).encode()).hexdigest()

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def validate_inputs(root=OUT,now=None):
    sup, director=load_inputs(root,now=now)
    operator=json.loads((root/"OPERATOR.json").read_text())
    if (operator.get("mode")!="internal_actions_only" or
        operator.get("source_utc")!=director["source_utc"] or
        operator.get("production_changed") is not False or
        operator.get("public_messaging_enabled") is not False or
        operator.get("public_messages_sent")!=0 or
        operator.get("external_actions")!=0 or
        operator.get("approval_required_for_all_external_actions") is not True):
        raise Reject("unapproved operator artifact")
    if operator.get("failures")!=0:
        raise Reject("operator validation failures")
    items=operator.get("tasks")
    if not isinstance(items,list) or len(items)>40:
        raise Reject("invalid operator tasks")
    intended={t["id"]:t for t in director["tasks"]}
    if len(items)!=len(intended) or operator.get("checked")!=len(items):
        raise Reject("partial operator scope")
    records={}
    for it in items:
        if not isinstance(it,dict):
            raise Reject("invalid operator task entry")
        tid=it.get("id")
        if tid not in intended or tid in records or tid not in ALLOWED:
            raise Reject("unknown operator task")
        if (it.get("requires_human_approval") is not True or
            it.get("priority")!=intended[tid]["priority"] or
            it.get("state") not in ("blocked","awaiting_human","awaiting_qa",
                                    "checked_needs_review","needs_attention")):
            raise Reject("unsafe operator task state")
        details=it.get("details")
        if not isinstance(details,dict):
            raise Reject("invalid operator details")
        records[tid]=it
    return director,records

def db_setup(db):
    db.execute("""CREATE TABLE IF NOT EXISTS work_items(
      task_id TEXT PRIMARY KEY,area TEXT NOT NULL,priority TEXT NOT NULL,
      state TEXT NOT NULL,identity TEXT NOT NULL,first_seen TEXT NOT NULL,
      last_seen TEXT NOT NULL,change_count INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      occurred TEXT NOT NULL, task_id TEXT NOT NULL,
      event_type TEXT NOT NULL, state TEXT NOT NULL, role TEXT NOT NULL,
      priority TEXT NOT NULL, identity TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS dispatch(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      day TEXT NOT NULL,issued TEXT NOT NULL,
      status TEXT NOT NULL)""")

def changes(db,director,operator,now):
    current=db.execute("SELECT task_id,identity,state FROM work_items").fetchall()
    before={id:{"identity":h,"state":state} for id,h,state in current}
    intended={t["id"]:t for t in director["tasks"]}
    delta=[]
    for task_id in sorted(operator):
        t=intended[task_id]
        op=operator[task_id]
        # Do not include rolling check counts or transient source timestamps.
        identity=digest({"state":op["state"],"details":op["details"],
                         "evidence":t.get("evidence") or {}})
        prior=before.get(task_id)
        if prior is None:
            event="detected"
        elif prior["state"]=="not_in_current_snapshot":
            event="reappeared"
        elif prior["identity"]!=identity:
            event="changed"
        else:
            event=None
        db.execute("""INSERT INTO work_items(task_id,area,priority,state,identity,
            first_seen,last_seen,change_count) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(task_id) DO UPDATE SET area=excluded.area,
            priority=excluded.priority,state=excluded.state,identity=excluded.identity,
            last_seen=excluded.last_seen,
            change_count=work_items.change_count+?""",
            (task_id,t["area"],t["priority"],op["state"],identity,now,now,
             1 if event else 0,1 if event else 0))
        if event:
            delta.append({"task_id":task_id,"event":event,"role":ROLE[t["area"]],
                          "priority":t["priority"],"state":op["state"]})
            db.execute("""INSERT INTO events(occurred,task_id,event_type,state,
               role,priority,identity) VALUES(?,?,?,?,?,?,?)""",
               (now,task_id,event,op["state"],ROLE[t["area"]],t["priority"],identity))
    # Disappearance is not completion: keep unresolved record, flag it once.
    vanished=sorted(set(before)-set(operator))
    for task_id in vanished:
        if before[task_id]["state"]!="not_in_current_snapshot":
            record=db.execute("SELECT area,priority FROM work_items WHERE task_id=?",
                              (task_id,)).fetchone()
            area,priority=record
            db.execute("UPDATE work_items SET state='not_in_current_snapshot',last_seen=? WHERE task_id=?",
                       (now,task_id))
            delta.append({"task_id":task_id,"event":"not_observed",
                          "role":ROLE[area],"priority":priority,
                          "state":"not_in_current_snapshot"})
            db.execute("""INSERT INTO events(occurred,task_id,event_type,state,
               role,priority,identity) VALUES(?,?,?,?,?,?,?)""",
               (now,task_id,"not_observed","not_in_current_snapshot",
                ROLE[area],priority,before[task_id]["identity"]))
    db.execute("""DELETE FROM events WHERE id NOT IN(
         SELECT id FROM events ORDER BY id DESC LIMIT ?)""",(MAX_HISTORY,))
    return delta

def queue(db):
    rows=db.execute("""SELECT task_id,area,priority,state,change_count,last_seen
                  FROM work_items ORDER BY CASE priority
                  WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END,task_id""").fetchall()
    return [{"task_id":id,"area":area,"role":ROLE[area],"priority":priority,
             "state":state,"changes":cnt,"last_seen":last}
            for id,area,priority,state,cnt,last in rows]

def render(report):
    rows=["# SoftMobile — cambios operativos internos",
          "Solo lectura y propuestas. Nunca habilita ventas ni mensajes públicos.",
          "UTC: "+report["at"],"Nuevos cambios: "+str(len(report["events"])),
          "En la cola: "+str(report["queued"]),
          "Acciones públicas: 0; pagos: 0; descuentos: 0; despliegues: 0.",
          "","## Eventos detectados"]
    for ev in report["events"]:
        rows.append("- "+ev["role"]+"/"+ev["priority"]+": "+ev["task_id"]+
                    " -> "+ev["event"]+" / "+ev["state"])
    if not report["events"]:
        rows.append("- Sin cambios desde el último ciclo.")
    rows.append("\n## Cola")
    for t in report["work_queue"]:
        rows.append("- "+t["priority"]+" | "+t["role"]+" | "+t["task_id"]+
                    " | "+t["state"])
    rows.append("\nLas desapariciones del reporte no prueban que una tarea se resolvió.")
    return "\n".join(rows)+"\n"

def dispatch_roles(db,events,now):
    # Only high-priority NEW/CHANGED issues requiring actual attention.
    roles={x.get("role") for x in events if x.get("priority")=="alta" and
           x.get("event") in ("detected","changed","reappeared") and
           x.get("state") in ("needs_attention","awaiting_human","awaiting_qa")}
    day=now[:10]
    dispatched=db.execute("SELECT COUNT(*) FROM dispatch WHERE day=?",
                          (day,)).fetchone()[0]
    remaining=max(0,MAX_EVENT_DISPATCHES_PER_DAY-dispatched)
    return [role for role in ROLE_ORDER if role in roles][:remaining]

def should_dispatch(db,events,now):
    return bool(dispatch_roles(db,events,now))

def send_internal_review(role):
    """Verify the exact role's restricted job before triggering OpenClaw."""
    if role not in ROLE_JOB_IDS:
        return False
    job_id=ROLE_JOB_IDS[role]
    base=["docker","exec","-u","node","openclaw-lab","node","dist/index.js"]
    try:
        spec=subprocess.run(base+["cron","list","--json"],capture_output=True,
                            text=True,timeout=15,check=False)
        if spec.returncode!=0:
            return False
        data=json.loads(spec.stdout)
        jobs=data.get("jobs",[])
        matched=[j for j in jobs if j.get("id")==job_id]
        if len(matched)!=1:
            return False
        job=matched[0]
        payload=job.get("payload") or {}
        if (job.get("enabled") is not True or
            job.get("sessionTarget")!="isolated" or
            (job.get("delivery") or {}).get("mode")!="none" or
            set(payload.get("toolsAllow",[]))!={"read","write"} or
            payload.get("kind")!="agentTurn"):
            return False
        cmd=base+["cron","run",job_id,"--json"]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=15,check=False)
        if proc.returncode!=0:
            return False
        resp=json.loads(proc.stdout)
        return resp.get("ok") is True and resp.get("enqueued") is True
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):
        return False

def run(root=OUT,dispatch=False,now=None):
    now=now or now_utc()
    director,operator=validate_inputs(root)
    # Atomic ledger transaction; no message contents, names or phone numbers.
    path=root/"events.sqlite3"
    with sqlite3.connect(path,timeout=8) as db:
        db.execute("BEGIN IMMEDIATE")
        db_setup(db)
        delta=changes(db,director,operator,now)
        work=queue(db)
        roles=dispatch_roles(db,delta,now) if dispatch else []
        for idx,role in enumerate(roles):
            db.execute("INSERT INTO dispatch(day,issued,status) VALUES(?,?,?)",
                       (now[:10],now+":"+str(idx),"reserved:"+role))
        db.commit()
    report={"schema_version":1,"mode":"internal_event_queue",
            "at":now,"source_utc":director["source_utc"],
            "public_messages_sent":0,"external_commercial_actions":0,
            "dispatched_review":False,"dispatched_roles":[],"queued":len(work),
            "events":delta,"work_queue":work}
    save(root/"EVENTS.json",json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    save(root/"EVENTS.md",render(report))
    failures=[]
    for idx,role in enumerate(roles):
        ok=send_internal_review(role)
        with sqlite3.connect(path,timeout=8) as db:
            db.execute("UPDATE dispatch SET status=? WHERE issued=?",
                       ("enqueued:"+role if ok else "failed:"+role,
                        now+":"+str(idx)))
        if ok:
            report["dispatched_roles"].append(role)
        else:
            failures.append(role)
    report["dispatched_review"]=bool(report["dispatched_roles"])
    save(root/"EVENTS.json",json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if failures:
        raise Reject("Restricted OpenClaw specialist could not be enqueued")
    os.chmod(path,0o600)
    return report

def main():
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("--dispatch",action="store_true",help="Trigger restricted internal OpenClaw review on new high-priority changes")
    args=a.parse_args()
    fd=os.open(LOCK,os.O_CREAT|os.O_RDWR,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print("router_busy");return 0
        try: r=run(dispatch=args.dispatch)
        except (Reject,OSError,ValueError,TypeError,KeyError,sqlite3.Error,
                subprocess.TimeoutExpired):
            print('event_router_blocked')
            return 2
        print(json.dumps({"status":"ok","events":len(r["events"]),
                         "queued":r["queued"],"review_enqueued":r["dispatched_review"],
                         "external_commercial_actions":0},ensure_ascii=False))
        return 0
    finally:
        os.close(fd)

if __name__=="__main__":
    raise SystemExit(main())
