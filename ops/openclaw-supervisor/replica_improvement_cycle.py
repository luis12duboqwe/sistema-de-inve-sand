#!/usr/bin/env python3
"""Independent follow-up on bounded Replica Skill sales fixes. No public actions."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import replica_cycle as base
import replica_seller_patch as patcher
import independent_seller_qa as fresh

ROOT = Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill")
FINAL = ROOT / "independent-review.json"
CANDIDATES = ROOT / "candidates"
REPORTS = Path("/opt/openclaw-lab/workspace/softmobile-supervisor")
KNOWN_PREFIXES = ("fin-approval-", "payment-received-", "optout-stop-")

def iso_utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def assert_reviewed_parent(report):
    parent = json.loads((ROOT / "latest.json").read_text())
    if (parent.get("mode") != "REPLICA_AUTONOMOUS_SALES_REVIEW"
        or parent.get("status") != "qa_passed_review_required"
        or parent.get("public_release_permitted") is not False
        or parent.get("auto_deployed") is not False
        or parent.get("qa_repeated") is not True
        or parent.get("source_sha256") != report["source_sha256"]
        or parent.get("candidate_sha256") != report["winning_candidate"]["sha256"]):
        raise base.Blocked("Replica pre-review not complete for same SHA")
    age = (datetime.now(timezone.utc) - iso_utc(parent["at"])).total_seconds()
    if not 0 <= age <= 60*60:
        raise base.Blocked("Replica pre-review is stale")
    return parent

def data_readiness():
    result = {}
    for filename, mode in (("CATALOG_AUDIT.json", "read_only_sales_catalog_aggregate"),
                           ("FINANCE_AUDIT.json", "finance_read_only_audit")):
        try:
            d=json.loads((REPORTS/filename).read_text())
            age=(datetime.now(timezone.utc)-iso_utc(d["at"])).total_seconds()
            if not 0 <= age <= 8*3600 or d.get("mode") != mode:
                raise ValueError("stale or invalid audit")
            if d.get("public_messages_sent") != 0 or d.get("inventory_updated") is True:
                raise ValueError("unexpected external activity in read-only report")
            if filename.startswith("CATALOG"):
                result["catalog"] = {
                    "freshness_from_partners_verified": d.get("stock_freshness_verified") is True
                        and d.get("price_freshness_verified") is True
                        and d.get("partner_stock_connected") is True,
                    "outbound_quote_authorized": d.get("outbound_customer_quote_authorized") is True,
                    "counts": {k:d.get("counts",{}).get(k) for k in
                        ("active_products", "stocked_active_products", "stocked_fully_specified",
                         "active_without_stock", "active_price_below_cost")},
                    "status": "verified_aggregate_only"}
            else:
                result["finance"] = {
                    "reconciliation_ready": d.get("financial_reconciliation_prerequisites") is True,
                    "revenue_verified": d.get("revenue_verified") is True,
                    "mismatched_totals": d.get("counts",{}).get("order_total_item_mismatch"),
                    "pending_orders": d.get("counts",{}).get("orders"),
                    "requires_human_accounting_review":
                       d.get("requires_human_accounting_review") is True,
                    "status": "verified_aggregate_only"}
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            result["catalog" if filename.startswith("CATALOG") else "finance"] = {
                "status":"source_missing_or_stale", "customer_data_extracted": False}
    return result

def run():
    prior, live_bytes, source_file = base.preflight()
    assert_reviewed_parent(prior)
    # This is a second test set, not the test set used to generate recipes.
    baseline = fresh.evaluate(source_file.read_text(encoding="utf-8"))
    failed = baseline["findings"]
    if any(not r["id"].startswith(KNOWN_PREFIXES) for r in failed):
        raise base.Blocked("new independent failures outside reviewed repair scope")
    if not failed:
        chosen = source_file
        change_kind = "no_fixes_required"
        proposal = prior["winning_candidate"]
    else:
        proposal = patcher.create()
        chosen = Path(proposal["candidate_file"])
        change_kind = "three_preapproved_guard_fixes"
    next_qa = fresh.evaluate(chosen.read_text(encoding="utf-8"))
    if next_qa["total"] != fresh.SCENARIO_COUNT or next_qa["failed"]:
        raise base.Blocked("improved candidate failed new independent rubric")
    full = base.qa_again(chosen)
    if full["passed"] is not True:
        raise base.Blocked("existing regression suite failed")
    if (sha256(live_bytes).hexdigest() != sha256(base.SOURCE.read_bytes()).hexdigest()
        or sha256(chosen.read_bytes()).hexdigest() != next_qa["sha256"]):
        raise base.Blocked("source or candidate changed while testing")
    checker = data_readiness()
    # The additional rubric is independent of generator recipes, NOT external certification.
    report = {
        "schema_version": 1, "mode": "REPLICA_ADDITIONAL_INDEPENDENT_FIX_REVIEW",
        "at": datetime.now(timezone.utc).isoformat(),
        "status": "qa_passed_manual_review_required",
        "scope": "sales_only", "source_sha256": prior["source_sha256"],
        "parent_candidate_sha256": prior["winning_candidate"]["sha256"],
        "candidate_sha256": next_qa["sha256"],
        "candidate_file": str(chosen),
        "patch_file": str(proposal.get("patch_file", "")),
        "change_type": change_kind,
        "new_rubric_before": {"passed": baseline["passed"], "total": baseline["total"],
                              "failed_ids": [r["id"] for r in failed]},
        "new_rubric_after": {"passed": next_qa["passed"], "total": next_qa["total"],
                             "failed_ids": []},
        "regressions": {"dialogues": full["dialogue"]["passed"],
            "heldout": full["heldout"]["passed"], "adversarial": full["adversarial"]["passed"],
            "rotating": full["rotating"]["passed"], "checkout": full["checkout"]["passed"],
            "unit_tests": full["unit_tests_passed"]},
        "commercial_data": checker,
        "independent_rubric_passed": True, "external_independent_certification": False,
        "real_customer_qa_verified": False, "manual_review_required": True,
        "public_release_permitted": False, "candidate_deployed": False,
        "public_messages_sent": 0, "payments_initiated": 0,
        "inventory_modified": False, "ai_api_calls": 0, "production_modified": False,
    }
    return report

def persist(d):
    base.write_atomic(FINAL, base.to_json(d))
    human = (
        "# Replica Skill — segunda rúbrica de calidad comercial\n\n"
        f"Estado: **{d['status']}**. No habilita lanzamiento.\n\n"
        f"SHA candidato: `{d.get('candidate_sha256', 'NO VERIFICADO')}`.\n"
        f"Antes: {d.get('new_rubric_before',{}).get('passed','?')}/"
        f"{d.get('new_rubric_before',{}).get('total','?')} escenarios.\n"
        f"Después: {d.get('new_rubric_after',{}).get('passed','?')}/"
        f"{d.get('new_rubric_after',{}).get('total','?')} escenarios.\n"
        "La segunda rúbrica es distinta de las pruebas originales, pero no es "
        "una certificación externa ni evidencia de ventas reales.\n\n"
        "## Restricciones\n\n"
        "- Fuente de stock/precios de aliados: no validada.\n"
        "- Órdenes y rentabilidad reales: pendientes de conciliación documental.\n"
        "- WhatsApp y despliegue público: última fase, bloqueados.\n"
        "- Ningún candidato se instala automáticamente.\n"
    )
    base.write_atomic(ROOT/"independent-review.md", human)

def main():
    try:
        report=run()
    except (base.Blocked, OSError, KeyError, TypeError, ValueError,
            RuntimeError, IndexError, TimeoutError) as err:
        report={"schema_version":1, "mode":"REPLICA_ADDITIONAL_INDEPENDENT_FIX_REVIEW",
            "at":datetime.now(timezone.utc).isoformat(),"status":"blocked",
            "reason":str(err)[:160],"manual_review_required":True,
            "public_release_permitted":False,"candidate_deployed":False,
            "public_messages_sent":0,"production_modified":False, "ai_api_calls":0}
    persist(report)
    print(json.dumps({"status":report["status"],
                      "sha": report.get("candidate_sha256"),
                      "reason": report.get("reason"),
                      "public_release_permitted": False}, ensure_ascii=False))
    return 0 if report["status"]=="qa_passed_manual_review_required" else 2

if __name__ == "__main__":
    raise SystemExit(main())