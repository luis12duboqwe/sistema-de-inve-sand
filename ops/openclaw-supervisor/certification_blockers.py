#!/usr/bin/env python3
"""Explain real SoftMobile release blockers without overriding certification gates.

Read only sanitized aggregated reports; never change orders, stock or messaging.
"""
from __future__ import annotations
from datetime import datetime,timezone
import json
from pathlib import Path
from hashlib import sha256
from release_gate import SALES_BLOCKERS
from supervisor import OUT,save

CERT=OUT/"CERTIFICATION.json"
FIN=OUT/"FINANCE_AUDIT.json"
CATALOG=OUT/"CATALOG_AUDIT.json"
AD=OUT/"META_ADS_EXTERNAL_SNAPSHOT.json"
QA=Path("/opt/softmobile-waha-test/approved-sales-pilot/approved-pilot-qa.json")
LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")

OWNERS={
    "independent_qa_converged":(
        "engineering", "Refresh source-bound independent code review against the current active seller, and verify two clean reviews without trusting historical frozen-suite results"),
    "real_ruby_reply_quality_passed":(
        "engineering", "Migrate SHA-pinned Ruby automation and promote reviewed code "
        "through reversible, private test release; repeat real Ruby QA"),
    "pilot_transport_verified":(
        "channel_setup", "Verify transport health in authorized pilot; do not turn on public "
        "WhatsApp before final phase"),
    "real_whatsapp_chatwoot_full_cycle_verified":(
        "channel_setup", "Confirm opt-in test conversation, incoming/outgoing receipts, "
        "human handoff, and no unintended public messages"),
    "followup_consent_policy_verified":(
        "engineering_and_privacy", "Persist customer no-contact opt-outs, enforce them across "
        "every sender and audit reset/retry paths"),
    "commercial_actions_authorized":(
        "business_owner_and_ops", "Validate ally stock, price, delivery, payment/financing "
        "and return policy; authorize allowed commercial operations"),
    "explicit_owner_launch_approval":(
        "business_owner", "Obtain distinct public-launch authorization only after the "
        "independent prelaunch technical and commercial conditions pass"),
    "real_orders_reconciled":(
        "accounting", "Resolve pending order statuses and discrepancies against actual "
        "payment/dispatch records; approve daily closings"),
    "meta_ads_data_connected":(
        "marketing", "Connect authenticated ongoing Meta Ads reporting into SoftMobile "
        "operations and verify refreshable campaigns and conversion attribution")
}
EXPECTED=set(OWNERS)|{
    "snapshot_consistent","internal_test_actions_safe",
    "chatwoot_pilot_coverage_verified","local_qa_passed",
    "fictional_sales_qa_passed","independent_qa_converged",
    "technical_patch_proposal_gate_healthy"
}

def report():
    c=json.loads(CERT.read_text())
    if (c.get("scope")!="sales_only" or c.get("mode")!="prelaunch_audit_only" or
        c.get("public_release_permitted") is not False or
        c.get("check_count")!=15 or
        set(c.get("checks",{}))!=EXPECTED or
        any(type(value) is not bool for value in c["checks"].values()) or
        c.get("passed_count")!=sum(c["checks"].values())):
        raise RuntimeError("certification format or source invalid")
    f=json.loads(FIN.read_text())
    catalog=json.loads(CATALOG.read_text())
    if f.get("source_utc")!=c.get("source_utc") or not f.get("read_only"):
        raise RuntimeError("finance source revision mismatched")
    if catalog.get("scope")!="sales_only" or catalog.get("inventory_updated") is not False:
        raise RuntimeError("catalog audit untrusted")
    diag={"schema_version":1,
          "mode":"read_only_release_blocker_diagnostics",
          "at":datetime.now(timezone.utc).isoformat(),
          "certification_at":c["at"],
          "source_utc":c["source_utc"],
          "approved_count":c["passed_count"],
          "total_count":c["check_count"],
          "public_release_permitted":False,
          "messages_sent":0,"payments_initiated":0,"production_modified":False,
          "blocked":[],
          "commercial_evidence":{
              "pending_orders":f["counts"]["orders"],
              "completed_orders":f["counts"]["orders_completed"],
              "approved_closes":f["counts"]["approved_closes"],
              "order_item_total_mismatches":f["counts"]["order_total_item_mismatch"],
              "non_card_mismatches":f["non_card_order_total_differences"],
              "possibly_fee_adjusted_mismatches":f["possible_fee_or_finance_adjustments"],
              "active_products":catalog["counts"]["active_products"],
              "active_without_stock":catalog["counts"]["active_without_stock"],
              "price_below_cost":catalog["counts"]["active_price_below_cost"],
              "stocked_missing_spec":catalog["counts"]["stocked_missing_required_quote_fields"],
              "partner_stock_price_verified":bool(
                 catalog.get("partner_stock_connected") is True and
                 catalog.get("stock_freshness_verified") is True and
                 catalog.get("price_freshness_verified") is True)
          },
          "approved_pilot_qa_verified":False,
          "ads_connector_in_chat_but_not_operational":False}
    try:
        approved=json.loads(QA.read_text())
        approval=json.loads(QA.with_name("approval.json").read_text())
        diag["approved_pilot_qa_verified"]=(
             approved.get("status")=="passed_internal_pilot_qa" and
             approved.get("candidate_sha256")==approval.get("candidate_sha256") and
             approval.get("public_channel_enabled") is False and
             approval.get("live_source_modified") is False and
             approved.get("public_release_permitted") is False and
             approved.get("deep_criteria_passed")==32 and
             approved.get("commercial_dialogues_passed")==72)
    except (OSError,ValueError,KeyError,TypeError):
        pass
    try:
        audit=json.loads(AD.read_text())
        diag["ads_connector_in_chat_but_not_operational"]=(
            audit.get("external_metrics_read_success") is True and
            audit.get("source_has_data_feed_to_vps") is False)
    except (OSError,ValueError):
        pass
    for k,passed in c["checks"].items():
        if passed:continue
        owner,needed=OWNERS[k]
        diag["blocked"].append({"gate":k,"owner_category":owner,"required_evidence":needed})
    if len(diag["blocked"]) != 15-c["passed_count"]:
        raise RuntimeError("blocker counts inconsistent")
    return diag

def main():
    d=report()
    save(OUT/"CERTIFICATION_BLOCKERS.json",json.dumps(d,ensure_ascii=False,indent=2)+"\n")
    lines=["# SoftMobile — Evidencia pendiente para el lanzamiento",
      "Certificación vigente: "+str(d["approved_count"])+"/"+str(d["total_count"]),
      "Salida pública: BLOQUEADA. No se alteran registros comerciales.",
      "",
      "## Bloqueos reales"]
    for b in d["blocked"]:
        lines.append("- **"+b["gate"]+"** — "+b["required_evidence"])
    cc=d["commercial_evidence"]
    lines+=["","## Datos internos por conciliar",
      "Órdenes pendientes: "+str(cc["pending_orders"]),
      "Órdenes completadas: "+str(cc["completed_orders"]),
      "Cierres aprobados: "+str(cc["approved_closes"]),
      "Diferencias entre total e ítems: "+str(cc["order_item_total_mismatches"]),
      "Stock activo sin unidades: "+str(cc["active_without_stock"]),
      "Productos debajo del costo: "+str(cc["price_below_cost"]),
      "",
      "El candidato aislado puede pasar sus pruebas mientras el vendedor activo "
      "todavía requiere integración. La publicidad conectada en ChatGPT no "
      "constituye una fuente operativa permanente dentro del VPS."]
    save(OUT/"CERTIFICATION_BLOCKERS.md","\n".join(lines)+"\n")
    print(json.dumps({"approved":d["approved_count"],"total":d["total_count"],
                      "blockers":len(d["blocked"]),
                      "public_release_permitted":False},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())