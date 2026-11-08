#!/usr/bin/env python3
"""Independent prelaunch certification; can never authorize public messaging.

Uses already sanitized supervisor/director/executor/events. Reports positive
technical evidence separately from hard external dependencies. No service,
message, campaign, stock, file outside workspace, or production mutation.
"""
from __future__ import annotations
from datetime import datetime,timezone
import json
from pathlib import Path

from pilot_executor import load_inputs, Reject
from supervisor import OUT, save

SALES_BLOCKERS=(
    "pilot_transport_verified",
    "real_whatsapp_chatwoot_full_cycle_verified",
    "independent_qa_converged",
    "followup_consent_policy_verified",
    "commercial_actions_authorized",
    "explicit_owner_launch_approval",
)
FULL_AUTONOMY_BLOCKERS=SALES_BLOCKERS+(
    "real_orders_reconciled",
    "repair_workflow_connected",
    "meta_ads_data_connected",
    "technical_patch_proposal_gate_healthy",
)

def validated_inputs(root=OUT):
    sup,director=load_inputs(root)
    op=json.loads((root/"OPERATOR.json").read_text())
    ev=json.loads((root/"EVENTS.json").read_text())
    src=director["source_utc"]
    if any(d.get("source_utc")!=src for d in (op,ev)):
        raise Reject("inconsistent source revisions")
    if (op.get("mode")!="internal_actions_only" or
        ev.get("mode")!="internal_event_queue" or
        op.get("failures")!=0 or
        ev.get("queued")!=len(ev.get("work_queue",[])) or
        type(op.get("checked")) is not int or
        op["checked"]!=len(op.get("tasks",[])) or
        op.get("production_changed") is not False or
        op.get("public_messaging_enabled") is not False or
        op.get("external_actions")!=0 or
        ev.get("external_commercial_actions")!=0 or
        op.get("public_messages_sent")!=0 or
        ev.get("public_messages_sent")!=0):
        raise Reject("unsafe certification context")
    return sup,director,op,ev

def checks(sup,director,op,ev):
    release=sup.get("release_gates") or {}
    quality=sup.get("quality") or {}
    health=sup.get("health") or {}
    chatwoot=sup.get("chatwoot") or {}
    synthetic=director.get("synthetic_sales") or {}
    fin=director.get("verified_finance") or {}
    ids={t.get("id"):t for t in director.get("tasks",[])}
    gates={
        "snapshot_consistent":True,
        "internal_test_actions_safe":(
            op.get("failures")==0 and op.get("public_messages_sent")==0
            and ev.get("public_messages_sent")==0
            and op.get("external_actions")==0),
        "chatwoot_pilot_coverage_verified":(
            chatwoot.get("coverage_complete") is True and
            chatwoot.get("account_id")==2 and chatwoot.get("inbox_id")==2),
        "local_qa_passed":quality.get("all_local_tests_passed") is True,
        "fictional_sales_qa_passed":(
            synthetic.get("available") is True and
            type(synthetic.get("scenarios")) is int and
            synthetic.get("scenarios")>=72 and
            synthetic.get("failed")==0 and
            synthetic.get("passed")==synthetic.get("scenarios")),
        "pilot_transport_verified":(
            release.get("pilot_transport_online") is True and
            health.get("whatsapp_online") is True),
        "real_whatsapp_chatwoot_full_cycle_verified":False,
        "independent_qa_converged":(
            release.get("independent_qa_converged") is True and
            quality.get("independent_convergence") is True),
        "followup_consent_policy_verified":False,
        "commercial_actions_authorized":(
            release.get("commercial_actions_enabled") is True),
        "explicit_owner_launch_approval":False,
        "real_orders_reconciled":(
            fin.get("profit_verified") is True and
            type(fin.get("completed_orders")) is int and fin["completed_orders"]>0
            and type(fin.get("daily_closes")) is int and fin["daily_closes"]>0),
        # Absence of an alert is NOT positive evidence of integration.
        "repair_workflow_connected":False,
        "meta_ads_data_connected":False,
        "technical_patch_proposal_gate_healthy":False
    }
    return gates

def report(sup,director,op,ev,now=None):
    gates=checks(sup,director,op,ev)
    sales=[k for k in SALES_BLOCKERS if gates[k] is not True]
    full=[k for k in FULL_AUTONOMY_BLOCKERS if gates[k] is not True]
    out={"schema_version":1,"mode":"prelaunch_audit_only",
         "at":now or datetime.now(timezone.utc).isoformat(),
         "source_utc":director["source_utc"],
         "checks":gates,
         "passed_count":sum(v is True for v in gates.values()),
         "check_count":len(gates),
         "blocked_sales_launch":sales,
         "blocked_full_autonomy":full,
         # Always fail-closed; even all technical checks true require an
         # independent operator-approved rollout outside this program.
         "public_release_permitted":False,
         "public_messages_sent":0,
         "production_changed":False,
         "qa_simulation_not_real_sale":True,
         "requires_explicit_manual_release_process":True}
    return out

def markdown(r):
    rows=["# SoftMobile — Certificación de prelanzamiento",
          "UTC: "+r["at"],"Evidencia: "+r["source_utc"],
          "Comprobaciones satisfechas: "+str(r["passed_count"])+"/"+str(r["check_count"]),
          "Lanzamiento público: BLOQUEADO (independiente de las pruebas locales).",
          "Mensajes a clientes: 0. Ventas reales verificadas por el simulador: 0.",
          "","## Comprobaciones"]
    for k,v in r["checks"].items():
        rows.append("- "+("[OK]" if v else "[PENDIENTE]")+" "+k)
    rows.append("\n## Bloqueos para el lanzamiento comercial")
    for k in r["blocked_sales_launch"]:
        rows.append("- "+k)
    rows.append("\n## Bloqueos adicionales para autonomía completa")
    for k in r["blocked_full_autonomy"]:
        if k not in SALES_BLOCKERS:
            rows.append("- "+k)
    rows.extend(["","Nunca activar público automáticamente desde este informe.",
      "La autorización explícita se da fuera del laboratorio luego de verificar el canal real y los controles."])
    return "\n".join(rows)+"\n"

def main():
    try:
        sup,director,op,ev=validated_inputs()
    except (Reject,ValueError,TypeError,KeyError,OSError) as exc:
        print("certification_rejected:"+type(exc).__name__)
        return 2
    out=report(sup,director,op,ev)
    save(OUT/"CERTIFICATION.json",json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"CERTIFICATION.md",markdown(out))
    print(json.dumps({"result":"blocked_prelaunch","checks_passed":out["passed_count"],
        "sales_blockers":len(out["blocked_sales_launch"]),
        "full_autonomy_blockers":len(out["blocked_full_autonomy"]),
        "public_release_permitted":False},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
