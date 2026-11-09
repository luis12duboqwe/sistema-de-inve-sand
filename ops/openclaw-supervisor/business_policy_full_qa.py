#!/usr/bin/env python3
"""Business-policy v2026-11-06 regression replacing only obsolete reservation rules.

All other historical conditions are evaluated unchanged using the real
Ruby binary in a networkless disposable container. No public actions.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,sys

LAB=Path("/opt/softmobile-waha-test/laboratorio-ia")
sys.path.insert(0,str(LAB))
import sales_conversation_quality as dialogue
import conversion_training_lab as legacy_dialogue
import sales_heldout_challenges as held
import sales_adversarial_quality as edges
import sales_rotating_challenges as rotate
import sales_autofix_loop as autofix
from inventory_training_lab import parse_with_real_ruby
from deep_sales_dialogue_lab import run as deep_dialogues
from deep_sales_quality_gate import run as deep_grade,at as deep_at

sys.path.insert(0,"/opt/openclaw-lab/supervisor")
import business_policy_sales_qa as new_policy

def denials(text):
    s=dialogue.fold(text)
    return (all(k in s for k in ("no hacemos","reservas","apartados"))
            and "cuando estes listo" in s
            and not any(k in s for k in ("apartado confirmado","ya te lo guardamos","ya lo reservamos")))

def from_traces(tasks,source,grader):
    records=[]
    for i in range(0,len(tasks),12):
        subset=tasks[i:i+12]
        actual=parse_with_real_ruby([{"id":x["id"],"messages":x["messages"],"expected":"not_found"}
                    for x in subset],source=source)
        if len(actual)!=len(subset): raise RuntimeError("missing Ruby responses")
        records.extend(grader(t,obs) for t,obs in zip(subset,actual))
    return records

def held_score(task,trace):
    if task["family"]!="reservation":
        return held.score(task,trace)
    good=(trace["id"]==task["id"] and len(trace["steps"])==3 and
          denials(trace["steps"][-1].get("baseline","")))
    return {"id":task["id"],"family":"reservation","passed":good,
            "rule":"2026-11-06_no_reservations_explicit"}

def edge_score(task,trace):
    idx=int(task["id"].split("-")[-1])
    name=edges.ROWS[idx][0]
    if not name.startswith("reserve_"):
        return edges.score(task,trace)
    good=(trace["id"]==task["id"] and len(trace["steps"])==3 and
          denials(trace["steps"][-1].get("baseline","")))
    return {"id":task["id"],"topic":name,"passed":good,
            "rule":"2026-11-06_no_reservations_explicit"}

def score_independent(case,trace):
    if case[1]!="reservation":
        return __import__("independent_seller_qa").score(case,trace)
    good=(trace["id"]==case[0] and len(trace["steps"])==len(case[2])
          and denials(trace["steps"][-1].get("baseline","")))
    return {"id":case[0],"passed":good,"policy_no_reservations":True}

def evaluate(source):
    digest=sha256(source.encode()).hexdigest()
    policy=new_policy.grade(source)
    old_dialog=dialogue.run(source=source,persist=False)
    # Legacy 72 includes 12 scripted "simulated_hold" cases, which are
    # explicitly forbidden by the Nov 6 approved commercial playbook. Score
    # the remaining 60 unchanged and independently verify each of 12 denials.
    legacy_families=old_dialog["by_family"]
    other_families=[v for k,v in legacy_families.items() if k!="reservation"]
    other_passed=sum(v["passed"] for v in other_families)
    reserve_cases=[r for r in legacy_dialogue.make_scenarios() if r["kind"]=="reservation"]
    def score_reserve(task,trace):
        valid=(len(trace.get("steps",[]))==4 and
               trace.get("id")==task["id"] and
               denials(trace["steps"][1].get("baseline","")) and
               denials(trace["steps"][2].get("baseline","")) and
               "exist" in dialogue.fold(trace["steps"][3].get("baseline","")))
        return {"id":task["id"],"passed":valid}
    rescores=from_traces(reserve_cases,source,score_reserve)
    policy_72=other_passed+sum(x["passed"] for x in rescores)
    hold=from_traces(held.items(),source,held_score)
    adv=from_traces(edges.records(),source,edge_score)
    rotating=from_traces(rotate.tasks(),source,held_score)
    import independent_seller_qa as independent
    independents=from_traces(
       [{"id":c[0],"messages":c[2]} for c in independent.CASES],source,
       lambda task,trace: score_independent(next(c for c in independent.CASES if c[0]==task["id"]),trace))
    deep=deep_dialogues(source)
    deep_old=deep_grade(deep)
    failure_set={(x["case"],x["turn"],x["check"]) for x in deep_old["failed_probes"]}
    override=("followup-sales-journey",12,"reservation_for_tomorrow_addressed")
    if failure_set-{override}:raise RuntimeError("new deep failing cases: "+str(failure_set-{override}))
    deep_deny=denials(deep_at(deep,"followup-sales-journey",12)["reply"])
    deep_approved=(deep_old["checks"]==32 and
                   deep_old["passed"]==31 and failure_set=={override} and deep_deny)
    checkout=autofix.legacy_regression(source)
    units=autofix.unit_regression()
    results={
     "schema_version":1, "mode":"RUBY_SALES_POLICY_NOV_6_REVALIDATION",
     "at":datetime.now(timezone.utc).isoformat(),"source_sha256":digest,
     "historical_72":old_dialog["passed"],
     "policy_72":policy_72,
     "historical_legacy_reservation_failures_expected":old_dialog["by_family"]["reservation"]["tested"]-old_dialog["by_family"]["reservation"]["passed"],
     "policy_reservations_correctly_denied":sum(x["passed"] for x in rescores),
     "new_commercial_policy_20":policy["passed"],
     "new_commercial_policy_total":policy["total"],
     "heldout_policy_passed":sum(x["passed"] for x in hold),"heldout_total":len(hold),
     "edge_policy_passed":sum(x["passed"] for x in adv),"edge_total":len(adv),
     "rotating_policy_passed":sum(x["passed"] for x in rotating),"rotating_total":len(rotating),
     "independent_policy_passed":sum(x["passed"] for x in independents),
     "independent_total":len(independents),
     "deep_criteria_policy_passed":32 if deep_approved else deep_old["passed"],
     "deep_criteria_total":32,
     "deep_legacy_obsolete_checks":list(failure_set) if deep_approved else [],
     "fictional_checkout_passed":checkout,
     "unit_tests_passed":units,
     "failed_case_ids":[x["id"] for results in (hold,adv,rotating,independents) for x in results if not x["passed"]],
     "production_modified":False,"public_messages_sent":0,
     "customer_data_loaded":False,"financing_authorized":False,
     "real_stock_verified":False,"deployment_permitted":False}
    results["passed"]=bool(
       other_passed==60 and policy_72==72 and len(rescores)==12 and
       policy["passed"]==20 and policy["total"]==20 and
       results["heldout_policy_passed"]==18 and results["heldout_total"]==18 and
       results["edge_policy_passed"]==11 and results["edge_total"]==11 and
       results["rotating_policy_passed"]==6 and results["rotating_total"]==6 and
       results["independent_policy_passed"]==22 and results["independent_total"]==22 and
       deep_approved and checkout==72 and units>=68 and not results["failed_case_ids"])
    return results

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit(2)
    candidate=Path(sys.argv[1])
    if candidate.is_symlink() or not candidate.is_file():raise RuntimeError("invalid source")
    obj=evaluate(candidate.read_text(encoding="utf-8"))
    print(json.dumps(obj,ensure_ascii=False))
    raise SystemExit(0 if obj["passed"] else 2)