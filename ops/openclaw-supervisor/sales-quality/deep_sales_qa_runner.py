#!/usr/bin/env python3
"""Automatic independent 10x15 buyer-journey safety gate for SoftMobile.

Reads ONLY synthetic buyer fixtures and staged code from reviewed autonomous
laboratory. Never imports the public bot, writes stock, messages clients or
changes an existing PR. Python returns aggregate evidence to the director.
"""
import hashlib,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
import deep_sales_dialogue_lab as deep
import deep_sales_quality_gate as assess
from quality_auditor import _atomic_json
ROOT=Path(__file__).resolve().parent
AUTOFIX=ROOT/"quality"/"autonomous-sales/latest.json"
DIR=ROOT/"quality"/"deep-sales-qa"
SUPERVISOR=Path("/opt/openclaw-lab/workspace/softmobile-supervisor")
SOURCE=deep.BOT
OUT=SUPERVISOR/"DEEP_SALES_QA.json"
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def audit():
    raw=json.loads(AUTOFIX.read_text())
    original=SOURCE.read_text()
    if (raw.get("scope")!="sales_only" or
        raw.get("environment")!="OFFLINE_AUTONOMOUS_SALES" or
        raw.get("status")!="qa_passed_review_required" or
        raw.get("source_sha256")!=digest(original) or
        raw.get("candidate_deployed") is not False or
        raw.get("public_messages_sent")!=0 or
        raw.get("real_inventory_modified") is not False or
        raw.get("deployment_authorized") is not False):
        raise ValueError("autofix source or safety not verified")
    meta=raw.get("winning_candidate") or {}
    target=Path(meta.get("candidate_file",""))
    expected_parent=AUTOFIX.parent/"candidates"
    if (target.is_symlink() or target.parent!=expected_parent or
        not target.is_file() or meta.get("auto_deploy") is not False):
        raise ValueError("candidate path not trusted")
    candidate=target.read_text()
    if digest(candidate)!=meta.get("sha256"):
        raise ValueError("staged candidate changed")
    actual=deep.run()
    patched=deep.run(source=candidate)
    a=assess.run(actual)
    b=assess.run(patched)
    if (actual["source_sha256"]!=raw["source_sha256"] or
        patched["source_sha256"]!=meta["sha256"] or
        actual["public_messages_sent"]!=0 or
        patched["public_messages_sent"]!=0 or
        not (a["checks"]==b["checks"]==32) or
        actual["turn_count"]!=150 or patched["turn_count"]!=150):
        raise ValueError("deep dialogue results not aligned")
    DIR.mkdir(mode=0o700,exist_ok=True)
    _atomic_json(DIR/"current-10x15.json",actual)
    _atomic_json(DIR/"candidate-10x15.json",patched)
    _atomic_json(DIR/"current-evaluation.json",a)
    _atomic_json(DIR/"candidate-evaluation.json",b)
    report={
     "schema_version":1,"at":datetime.now(timezone.utc).isoformat(),
     "mode":"deep_sales_synthetic_independent_gate","scope":"sales_only",
     "current_ruby_sha256":raw["source_sha256"],
     "candidate_sha256":meta["sha256"],
     "buyer_dialogues":10,"buyer_turns_each":15,"buyer_messages":150,
     "quality_checks":32,
     "live_ruby_passed":a["passed"],"candidate_passed":b["passed"],
     "candidate_failed":b["failed"],
     "failed_probes":b["failed_probes"],
     "candidate_fully_approved":b["independent_full_customer_qa_passed"],
     "status":"review_required" if b["independent_full_customer_qa_passed"] else "deep_qa_failures_block_launch",
     "customer_data_used":False,"real_sales_verified":0,
     "public_messages_sent":0,"production_changed":False,
     "candidate_deployed":False,"public_release_permitted":False
    }
    _atomic_json(OUT,report)
    (SUPERVISOR/"DEEP_SALES_QA.md").write_text(
      "# SoftMobile — pruebas profundas de ventas\n\n"
      "Solo conversaciones ficticias con respuesta Ruby real en Docker sin red.\n"
      f"Mensajes: 150, 10 diálogos de 15 turnos; {report['quality_checks']} verificaciones.\n"
      f"Ruby actual: {a['passed']}/32; candidato: {b['passed']}/32.\n"
      f"Fallos no resueltos: {b['failed']} (detalle en DEEP_SALES_QA.json).\n"
      "No despliegue, cobros, clientes, stock ni WhatsApp. El candidato sigue pendiente.\n")
    return report
if __name__=="__main__":
 try:
  r=audit()
 except (OSError,ValueError,TypeError,KeyError,RuntimeError):
  print(json.dumps({"status":"blocked_source_or_sandbox_error",
    "public_messages_sent":0,"production_changed":False}))
  raise SystemExit(2)
 print(json.dumps({"status":r["status"],"buyer_dialogues":10,
  "buyer_messages":150,"quality_checks":32,"current_passed":r["live_ruby_passed"],
  "candidate_passed":r["candidate_passed"],
  "public_messages_sent":0,"production_changed":False}))
