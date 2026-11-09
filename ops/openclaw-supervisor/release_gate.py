#!/usr/bin/env python3
"""Independent prelaunch certification; can never authorize public messaging.

Uses already sanitized supervisor/director/executor/events. Reports positive
technical evidence separately from hard external dependencies. No service,
message, campaign, stock, file outside workspace, or production mutation.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import sys
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

def independent_source_proof():
    """Verify the actual offline proposal guard against the CURRENT Ruby source.

    Not a deployment permission: the known SHA and the exact Ruby anchor must
    match, and the patch recipe parser must identify only that unique anchor.
    """
    try:
        import patch_source_compat as compat
        bot=compat.BOT
        if bot.is_symlink() or not bot.is_file():
            return {"validated":False}
        source=bot.read_text(encoding="utf-8")
        if not compat.compatible(source):
            return {"validated":False}
        sys.path.insert(0,"/opt/softmobile-waha-test/laboratorio-ia")
        import patch_proposer as proposer
        proposer.COLOR_ANCHOR=compat.SAFETY_ANCHOR
        _,method,_=proposer.method_area(source)
        if method.count(compat.SAFETY_ANCHOR)!=1:
            return {"validated":False}
        return {"validated":True,"live_sha256":sha256(source.encode()).hexdigest(),
                "safe_scope":"proposal-only","deployment_permitted":False}
    except (OSError,ValueError,RuntimeError,TypeError,KeyError,UnicodeError):
        return {"validated":False}


def approved_internal_pilot_proof():
    """Only OFFLINE candidate QA, never evidence of public or live Ruby quality."""
    try:
        import approve_sales_pilot as approval
        from pathlib import Path
        root=approval.DIR
        if root.is_symlink() or approval.DEST.is_symlink() or approval.MANIFEST.is_symlink():
            return {"validated":False}
        manifest=json.loads(approval.MANIFEST.read_text())
        qa=json.loads((root/"approved-pilot-qa.json").read_text())
        stamp=datetime.fromisoformat(qa["at"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-stamp).total_seconds()
        if not 0<=age<=9*3600:
            return {"validated":False}
        if (manifest.get("approved_for")!="offline_internal_pilot_only" or
            manifest.get("status")!="approved_candidate_bundle_staged" or
            manifest.get("owner_authorized_internal_pilot") is not True or
            manifest.get("live_source_modified") is not False or
            manifest.get("public_channel_enabled") is not False or
            qa.get("mode")!="APPROVED_SALES_PILOT_OFFLINE_REGRESSION" or
            qa.get("status")!="passed_internal_pilot_qa" or
            qa.get("public_release_permitted") is not False or
            qa.get("public_messages_sent")!=0 or
            qa.get("production_modified") is not False or
            qa.get("deep_dialogues")!=10 or qa.get("deep_turns")!=150 or
            qa.get("deep_criteria_passed")!=32 or qa.get("heldout_new_passed")!=13 or
            qa.get("extra_independent_passed")!=22 or
            qa.get("commercial_dialogues_passed")!=72 or
            qa.get("unit_tests_passed",0)<68 or
            manifest.get("candidate_sha256")!=approval.SHA or
            qa.get("candidate_sha256")!=approval.SHA or
            manifest.get("source_sha256")!=approval.BASE_SHA or
            sha256(approval.DEST.read_bytes()).hexdigest()!=approval.SHA or
            sha256(approval.LIVE.read_bytes()).hexdigest()!=approval.BASE_SHA):
            return {"validated":False}
        return {"validated":True,"candidate_sha256":approval.SHA,
                "live_source_sha256":approval.BASE_SHA,"source":"approved_internal_pilot",
                "public_release_permitted":False}
    except (OSError,ValueError,RuntimeError,TypeError,KeyError,UnicodeError,AttributeError):
        return {"validated":False}


def checks(sup,director,op,ev,source_proof=None):
    release=sup.get("release_gates") or {}
    quality=sup.get("quality") or {}
    health=sup.get("health") or {}
    chatwoot=sup.get("chatwoot") or {}
    synthetic=director.get("synthetic_sales") or {}
    seller=director.get("seller_reply_quality") or {}
    fin=director.get("verified_finance") or {}
    ids={t.get("id"):t for t in director.get("tasks",[])}
    proof=source_proof or {}
    source_gate_ok=(
        proof.get("validated") is True and
        proof.get("safe_scope")=="proposal-only" and
        proof.get("deployment_permitted") is False and
        proof.get("live_sha256")==seller.get("ruby_source_sha256") and
        seller.get("available") is True)
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
        "real_ruby_reply_quality_passed":(
            seller.get("available") is True and
            seller.get("scenarios")==72 and
            seller.get("passed")==72 and seller.get("failed")==0),
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
        "technical_patch_proposal_gate_healthy":source_gate_ok
    }
    return gates

def offline_status(sup,director,op,ev,finance=None,repairs=None,source_proof=None,approved_pilot=None):
    finance=finance or {}
    repairs=repairs or {}
    src=director["source_utc"]
    finance_verified=(
        finance.get("source_utc")==src and
        finance.get("mode")=="finance_read_only_audit" and
        finance.get("read_only") is True and
        finance.get("customer_data_extracted") is False and
        finance.get("payments_initiated")==0 and
        finance.get("revenue_verified") is False and
        finance.get("profit_verified") is False)
    repairs_lab=(
        repairs.get("source_utc")==src and
        repairs.get("mode")=="repair_simulation_and_source_probe" and
        repairs.get("offline_domain_cases")==60 and
        repairs.get("offline_domain_passed")==60 and
        repairs.get("real_repair_cases_processed")==0 and
        repairs.get("public_messages_sent")==0 and
        repairs.get("repair_workflow_connected") is False)
    proof=source_proof or {}
    approved=approved_pilot or {}
    original_seller=director.get("seller_reply_quality") or {}
    source_gate_ok=(
        proof.get("validated") is True and
        proof.get("safe_scope")=="proposal-only" and
        proof.get("deployment_permitted") is False and
        original_seller.get("available") is True and
        proof.get("live_sha256")==original_seller.get("ruby_source_sha256"))
    approved_deep_ok=(
        approved.get("validated") is True and
        approved.get("source")=="approved_internal_pilot" and
        approved.get("public_release_permitted") is False and
        approved.get("live_source_sha256")==original_seller.get("ruby_source_sha256") and
        original_seller.get("available") is True)
    quality=sup.get("quality") or {}
    sales=director.get("synthetic_sales") or {}
    inventory=sup.get("inventory") or {}
    return {
       "orchestration_and_internal_execution":(
          op.get("failures")==0 and ev.get("external_commercial_actions")==0),
       "inventory_read_only_available":(
          inventory.get("status")=="ok" and inventory.get("read_only") is True),
       "sales_simulation_proof_for_current_source":(
          sales.get("available") is True and
          type(sales.get("scenarios")) is int and sales["scenarios"]>=72 and
          sales.get("failed")==0),
       "ruby_sales_conversation_quality_passed":(
          director.get("seller_reply_quality",{}).get("available") is True and
          director["seller_reply_quality"].get("scenarios")==72 and
          director["seller_reply_quality"].get("passed")==72 and
          director["seller_reply_quality"].get("failed")==0),
       "deep_sales_15_turn_conversations_passed":approved_deep_ok or (
          director.get("deep_sales_quality",{}).get("available") is True and
          director["deep_sales_quality"].get("buyer_dialogues")==10 and
          director["deep_sales_quality"].get("buyer_messages")==150 and
          director["deep_sales_quality"].get("tested")==32 and
          director["deep_sales_quality"].get("candidate_passed")==32 and
          director["deep_sales_quality"].get("failed")==0 and
          director["deep_sales_quality"].get("independent_full_qa_converged") is True),
       "reference_only_ai_commercial_firewall_passed":(
          director.get("autonomous_sales",{}).get("available") is True and
          director["autonomous_sales"].get("reference_only_agent_firewall_verified") is True and
          type(director["autonomous_sales"].get("candidate_unit_tests_passed")) is int and
          director["autonomous_sales"]["candidate_unit_tests_passed"]>=68 and
          director["autonomous_sales"].get("candidate_deployed") is False),
       "autonomous_sales_review_candidate_staged":(
          director.get("autonomous_sales",{}).get("available") is True and
          director["autonomous_sales"].get("candidate_dialogues_passed")==72 and
          director["autonomous_sales"].get("candidate_rotating_passed")==6 and
          director["autonomous_sales"].get("candidate_deployed") is False and
          director["autonomous_sales"].get("manual_review_required") is True),
       "finance_audit_available":finance_verified,
       "repair_domain_synthetic_qa_passed":repairs_lab,
       "independent_quality_converged":quality.get("independent_convergence") is True,
       "real_financial_reconciliation":False,
       "real_repair_workflow_connected":False,
       "advertising_data_source_connected":False,
       "autonomous_code_review_source_gate":source_gate_ok,
    }

def report(sup,director,op,ev,now=None,finance=None,repairs=None,source_proof=None,approved_pilot=None):
    gates=checks(sup,director,op,ev,source_proof=source_proof)
    sales=[k for k in SALES_BLOCKERS if gates[k] is not True]
    full=[k for k in FULL_AUTONOMY_BLOCKERS if gates[k] is not True]
    offline=offline_status(sup,director,op,ev,finance,repairs,source_proof=source_proof,approved_pilot=approved_pilot)
    out={"schema_version":1,"mode":"prelaunch_audit_only",
         "at":now or datetime.now(timezone.utc).isoformat(),
         "source_utc":director["source_utc"],
         "checks":gates,
         "passed_count":sum(v is True for v in gates.values()),
         "check_count":len(gates),
         "blocked_sales_launch":sales,
         "blocked_full_autonomy":full,
         "non_whatsapp_readiness":offline,
         "non_whatsapp_passed":sum(v is True for v in offline.values()),
         "non_whatsapp_total":len(offline),
         "non_whatsapp_blockers":[k for k,v in offline.items() if v is not True],
         "offline_internal_pilot_candidate_verified":(approved_pilot or {}).get("validated") is True,
         "offline_internal_pilot_candidate_sha256":(approved_pilot or {}).get("candidate_sha256")
           if (approved_pilot or {}).get("validated") is True else None,
         "active_ruby_quality_distinct_from_offline_candidate":True,
         "whatsapp_deferred_until_final_phase":True,
         # Always fail-closed; even all technical checks true require an
         # independent operator-approved rollout outside this program.
         "public_release_permitted":False,
         "public_messages_sent":0,
         "production_changed":False,
         "qa_simulation_not_real_sale":True,
         "requires_explicit_manual_release_process":True}
    return out

def sales_scope_report(out,director):
    """Exclude explicitly paused repairs from active commercial readiness.

    WhatsApp public release remains blocked, but its work is deferred.
    The historical broad report() is retained for offline compatibility.
    """
    if (director.get("scope")!="sales_only" or
        out.get("public_release_permitted") is not False or
        out.get("public_messages_sent")!=0):
        raise Reject("sales certification scope invalid")
    sales_checks={k:v for k,v in out["checks"].items()
                  if k!="repair_workflow_connected"}
    offline={k:v for k,v in out["non_whatsapp_readiness"].items()
             if k not in ("repair_domain_synthetic_qa_passed",
                          "real_repair_workflow_connected")}
    return {**out,"scope":"sales_only",
        "excluded_modules":["repairs","employee_analytics"],
        "checks":sales_checks,
        "passed_count":sum(v is True for v in sales_checks.values()),
        "check_count":len(sales_checks),
        "blocked_full_autonomy":[b for b in out["blocked_full_autonomy"]
                                  if b!="repair_workflow_connected"],
        "non_whatsapp_readiness":offline,
        "non_whatsapp_passed":sum(v is True for v in offline.values()),
        "non_whatsapp_total":len(offline),
        "non_whatsapp_blockers":[k for k,v in offline.items() if v is not True],
        "public_release_permitted":False,
        "public_messages_sent":0}

def markdown(r):
    rows=["# SoftMobile — Certificación de prelanzamiento",
          "UTC: "+r["at"],"Evidencia: "+r["source_utc"],
          "Comprobaciones satisfechas: "+str(r["passed_count"])+"/"+str(r["check_count"]),
          "Lanzamiento público: BLOQUEADO (independiente de las pruebas locales).",
          "Mensajes a clientes: 0. Ventas reales verificadas por el simulador: 0.",
          "","## Comprobaciones"]
    for k,v in r["checks"].items():
        rows.append("- "+("[OK]" if v else "[PENDIENTE]")+" "+k)
    rows.append("\n## Trabajo SIN WhatsApp: "+str(r["non_whatsapp_passed"])+"/"+str(r["non_whatsapp_total"]))
    for k,v in r["non_whatsapp_readiness"].items():
        rows.append("- "+("[OK]" if v else "[PENDIENTE]")+" "+k)
    rows.append("\nWhatsApp se deja para la última fase.")
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
        finance=json.loads((OUT/"FINANCE_AUDIT.json").read_text())
        if (finance.get("source_utc")!=director["source_utc"] or
            finance.get("public_messages_sent")!=0):
            raise Reject("mismatched finance workstream")
        source_proof=independent_source_proof()
        approved_proof=approved_internal_pilot_proof()
        out=sales_scope_report(
            report(sup,director,op,ev,finance=finance,
                   source_proof=source_proof,approved_pilot=approved_proof),director)
    except (Reject,ValueError,TypeError,KeyError,OSError) as exc:
        print("certification_rejected:"+type(exc).__name__)
        return 2
    save(OUT/"CERTIFICATION.json",json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"CERTIFICATION.md",markdown(out))
    print(json.dumps({"result":"blocked_prelaunch","checks_passed":out["passed_count"],
        "sales_blockers":len(out["blocked_sales_launch"]),
        "full_autonomy_blockers":len(out["blocked_full_autonomy"]),
        "public_release_permitted":False},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())