#!/usr/bin/env python3
"""Bounded self-review and repair; only a quarantined copy may be edited."""
import difflib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import lab_cycle as q

# Bounded repair + two independent clean review turns within one isolated run.
# No production writes. Each remote model turn is reserved before invocation.
MAX_PASSES=3
MAX_DAILY_AGENT_CALLS=6
CLEAN_AUDIT_INTERVAL_HOURS=6
FAILING_AUDIT_INTERVAL_HOURS=6
DAILY_AGENT_LEDGER=q.RESULTS/"agent-calls-by-utc-day.json"
MINIMUM={"sales":127,"photos":10,"pilot":30}
CLEAN_REVIEW_LEDGER=q.RESULTS/"clean-review-ledger.json"

def audit_scope_fingerprint(stage,original):
    """Changes to any scoped implementation invalidate old clean-review credits."""
    manifest=[(name,q.sha(stage/name)) for name in sorted(original)
              if name.endswith(".py") and not Path(name).name.startswith("test_")
              and (stage/name).is_file()]
    # Changes to the test contract invalidate review credits too, even if
    # implementation files are unchanged.
    manifest.append(("commercial_policy_contract_sha",q.sha(q.POLICY_CONTRACT)))
    return hashlib.sha256(json.dumps(manifest,separators=(",",":")).encode()).hexdigest()

def recorded_clean_reviews(fingerprint):
    """Only prior independent, successful agent passes count; local tests alone do not."""
    try:
        saved=json.loads(CLEAN_REVIEW_LEDGER.read_text(encoding="utf-8"))
        count=saved.get("count",0)
        if (saved.get("scope_fingerprint")==fingerprint and
            type(count) is int and 0<=count<=2):
            return count
    except (OSError,ValueError,TypeError):
        pass
    return 0

def record_independent_review(fingerprint,clean,run_id):
    """A model-backed scoped review can increment, never a scheduled test-only run."""
    count=min(2,recorded_clean_reviews(fingerprint)+1) if clean else 0
    q.atomic_json(CLEAN_REVIEW_LEDGER,{
        "scope_fingerprint":fingerprint if clean else None,
        "count":count,
        "last_audit_run_id":run_id,
        "scoped_only":True,
        "production_ready":False,
    })
    return count
q.SUITES.append(("pilot","laboratorio-ia",[
    "test_agent_public_pilot","test_public_reply_guard","test_pilot_conversation_regressions",
    "test_buyer_self_review","test_pilot_bursts","test_choice_context","test_commercial_experience",
    "test_customer_journey_findings","test_real_groq_followup","test_bot_identity_disclosure","test_extended_buyer_phrasings","test_extended_round2","test_seller_voice","test_seller_style_coverage","test_commercial_variants","test_memory_rejection_quality","test_groq_sales_journeys","test_sales_natural_regressions","test_internal_handoff_language","test_delivery_conversation_regression","test_full_sales_journey_failures","test_second_complete_buyer_journey","test_sales_pipeline_conversion","test_first_greeting_reset","test_city_question_repetition",
    "test_pilot_memory","test_dialogue_slots","test_resilient_sales"]))

def files(stage):
    return {str(p.relative_to(stage)):q.sha(p)
        for p in stage.rglob("*") if p.is_file() and not p.is_symlink()}

def added(stage,initial):
    return sorted(n for n in files(stage) if n not in initial and
        re.fullmatch(r"(laboratorio-ia|staff-bridge)/test_[a-zA-Z0-9_]+[.]py",n)
        and n!="staff-bridge/test_openclaw_workflow_regressions.py"
        and n!="laboratorio-ia/test_commercial_policy_contract.py"  # already in commercial suite
        and "def test_" in (stage/n).read_text(encoding="utf-8",errors="replace"))

def run_tests(stage,run_id,step,initial):
    return q.test(stage,"check",q.RESULTS/(run_id+"-pass"+str(step)+".json"),
                  extra_tests=added(stage,initial))

def safe(stage,protected,base,initial):
    current=files(stage)
    bad=[n for n,h in protected.items() if current.get(n)!=h]
    bad.extend(n for n in current if n not in base and n.endswith(".py")
        and n not in added(stage,initial))
    bad.extend(str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_symlink())
    return sorted(set(bad))

def result_verdict(stage,step):
    try:
        d=json.loads((stage/("PASS_"+str(step)+".json")).read_text())
        return d.get("independent_review_complete") is True and d.get("verified_unresolved_errors")==[]
    except (OSError,ValueError,AttributeError):
        return False

def quota_available(now=None):
    """Fail closed on a corrupt existing quota ledger, unlike silent resets."""
    now=now or dt.datetime.now(dt.timezone.utc)
    try:
        if not DAILY_AGENT_LEDGER.exists():
            return MAX_DAILY_AGENT_CALLS
        data=json.loads(DAILY_AGENT_LEDGER.read_text())
        date=data.get("day_utc")
        count=data.get("calls")
        if (not isinstance(date,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date)
            or type(count) is not int or not 0<=count<=MAX_DAILY_AGENT_CALLS):
            return 0
        return MAX_DAILY_AGENT_CALLS-count if date==now.date().isoformat() else MAX_DAILY_AGENT_CALLS
    except (OSError,ValueError,TypeError,AttributeError):
        return 0

def reserve_model_call(now=None):
    """Atomic under the parent cycle.lock; never reset a same-day count."""
    now=now or dt.datetime.now(dt.timezone.utc)
    slots=quota_available(now)
    if slots<=0:
        return False
    used=MAX_DAILY_AGENT_CALLS-slots
    q.atomic_json(DAILY_AGENT_LEDGER,{"day_utc":now.date().isoformat(),
                 "calls":used+1,"cap":MAX_DAILY_AGENT_CALLS,
                 "last_reserved_utc":now.isoformat(),"production_ready":False})
    return True

def should_call_agent(tests,contract_sha=None):
    """Keep model use separate from local tests and the versioned policy gate."""
    failure=not tests or any(not r.get("passed") or r.get("tests",0)<=0
                            for r in tests.values())
    wait_hours=FAILING_AUDIT_INTERVAL_HOURS if failure else CLEAN_AUDIT_INTERVAL_HOURS
    ledger=q.RESULTS/"agent-budget.json"
    try:
        record=json.loads(ledger.read_text(encoding="utf-8"))
        previous=dt.datetime.fromisoformat(record["last_attempt_utc"])
        seconds=(dt.datetime.now(dt.timezone.utc)-previous).total_seconds()
        # When a newly audited policy test contract replaces unsafe historical
        # assertions, allow ONE fresh bounded review without waiting for
        # the old six-hour cooldown. Daily quota still applies.
        changed_contract=bool(contract_sha and record.get("policy_contract_sha")!=contract_sha)
        if seconds<wait_hours*3600 and not changed_contract:
            return False, max(0,int(wait_hours*3600-seconds)), failure, ledger
    except (OSError,ValueError,TypeError,KeyError):
        pass
    return True,0,failure,ledger

def main():
    q.SNAP.mkdir(parents=True,exist_ok=True)
    q.RESULTS.mkdir(parents=True,exist_ok=True)
    with (q.BASE/"integration"/"cycle.lock").open("a+") as lk:
        try: fcntl.flock(lk,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: print("Skipped overlap"); return 0
        run_id=q.stamp()
        stage=q.SNAP/run_id
        status={"run_id":run_id,"stage":str(stage),"mode":"offline_reaudit",
            "production_changed":False,"passes":[],"converged_tested_scope":False}
        try:
            # Local read-only analysis; share aggregate categories, never buyer text.
            from pilot_feedback import main as collect_pilot_feedback
            collect_pilot_feedback()
            original,carried=q.prepare(stage)
            initial=files(stage)
            protected={n:h for n,h in initial.items() if
                n.endswith(".json") or n.startswith("knowledge/") or
                Path(n).name.startswith("test_") or n in ("AGENTS.md","TASK.md")}
            tests=run_tests(stage,run_id,0,original)
            status["baseline"]={k:[v["tests"],v["passed"]] for k,v in tests.items()}
            evidence=stage/"BASELINE_TEST_RESULTS.txt"
            evidence.write_text("OFFLINE PRE-AUDIT RESULTS (not production verification)\n"+"\n".join(
                k+": "+str(v["tests"])+" tests, passed="+str(v["passed"])+"\n"+v["tail"][-1500:]
                for k,v in tests.items()),encoding="utf-8")
            os.chown(evidence,1000,1000)
            policy_sha=q.sha(q.POLICY_CONTRACT)
            allowed,remaining,failed,ledger=should_call_agent(tests,policy_sha)
            daily_remaining=quota_available()
            allowed=allowed and daily_remaining>0
            status["commercial_contract_sha256"]=policy_sha
            status["local_tests_passed"]=not failed
            status["model_invocations"]=0
            status["model_budget"]={"allowed":allowed,"cooldown_seconds":remaining,
                "max_calls_per_run":MAX_PASSES,"max_calls_per_utc_day":MAX_DAILY_AGENT_CALLS,
                "remaining_calls_today":daily_remaining,
                "clean_audit_interval_hours":CLEAN_AUDIT_INTERVAL_HOURS,
                "failing_audit_interval_hours":FAILING_AUDIT_INTERVAL_HOURS}
            if not allowed:
                status["stop_reason"]=("daily_model_budget_exhausted" if daily_remaining==0
                    else ("local_tests_failed_model_deferred" if failed
                    else "local_tests_passed_codex_saved"))
                status["post"]={k:{"tests":v["tests"],"passed":v["passed"]}
                    for k,v in tests.items()}
                status["end_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
                q.atomic_json(q.RESULTS/(run_id+"-status.json"),status)
                q.atomic_json(q.RESULTS/"latest.json",status)
                print(json.dumps({"run_id":run_id,"outcome":status["stop_reason"],
                    "model_calls":0,"cooldown_seconds":remaining,
                    "local_tests":status["post"]}),flush=True)
                return 2 if failed else 0
            # Reserve quota BEFORE invoking Codex; failed calls still consume quota.
            q.atomic_json(ledger,{"last_attempt_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
                "last_run_id":run_id,"reason":"reproducible_test_failure" if failed else "daily_scoped_review",
                "max_calls_this_run":MAX_PASSES,"policy_contract_sha":policy_sha})
            for n in range(1,MAX_PASSES+1):
                if not reserve_model_call():
                    status["stop_reason"]="daily_model_budget_exhausted"
                    break
                before=files(stage)
                task=stage/"ITERATION.md"
                task.write_text(
                    "LOW-TOKEN scoped QA: do not read the full repository. "
                    "Start with BASELINE_TEST_RESULTS.txt and CARRIED_PENDING_PATCH.md "
                    "if present, then inspect ONLY failing modules or pending patch files "
                    "and their direct dependencies. Do not re-audit passing untouched files. "
                    "Make the smallest correction for a REPRODUCED failure or inspect "
                    "a narrow pending change on this daily audit. "
                    "Read AGENTS.md and the summarized PILOT_FEEDBACK.json only if needed. "
                    "The pilot feedback has only heuristic issue counts, not "
                    "proof of customer defects. No actual buyer messages are provided. "
                    "Never contact real customers, load credentials, run deployments, "
                    "or touch files outside this snapshot. Add new regression tests; "
                    "do not change existing tests or trusted fixture files. "
                    "If a verified defect exists, fix the implementation here and retest. "
                    "Write PASS_"+str(n)+".json with strict JSON keys "
                    "independent_review_complete (boolean), "
                    "verified_unresolved_errors (list), summary (text). "
                    "independent_review_complete=true means ONLY that this bounded audit pass "
                    "rechecked the modified code and selected offline suites, with "
                    "no remaining reproducible defect found in that scope. "
                    "Set it false when you could not independently review the scoped changes, "
                    "or any verified bug remains unresolved. "
                    "Never claim that all real-world errors are eliminated. "
                    "Previous offline test results: "+
                    json.dumps({k:[v["tests"],v["passed"]] for k,v in tests.items()})+
                    "\n",encoding="utf-8")
                os.chown(task,1000,1000)
                status["model_invocations"]+=1
                call=subprocess.run(["docker","exec","openclaw-lab","node",
                    "dist/index.js","agent","--message",
                    "Perform independent review pass "+str(n)+" of "
                    "/home/node/.openclaw/workspace/lab-runs/"+run_id+
                    "/ITERATION.md. Inspect and improve only the corresponding "
                    "isolated workspace. Write PASS_"+str(n)+".json.",
                    "--session-id",run_id+"-audit-"+str(n),
                    "--model","openai/gpt-6-sol",
                    "--thinking","low","--timeout","180"],
                    capture_output=True,text=True,timeout=220,check=False)
                log=q.RESULTS/(run_id+"-agent-pass"+str(n)+".log")
                log.write_text(((call.stdout or "")+"\n"+
                    (call.stderr or ""))[-4000:],encoding="utf-8")
                current=files(stage)
                modified=[f for f in original if before.get(f)!=current.get(f)]
                violations=safe(stage,protected,initial,original)
                violations.extend(f for f in modified if not
                    (f=="staff-bridge/workflow.py" or
                    re.fullmatch(r"laboratorio-ia/(?!test_)[a-zA-Z0-9_]+[.]py",f)))
                if violations:
                    status["passes"].append({"pass":n,"safety_violations":violations})
                    status["stop_reason"]="unsafe_change"
                    break
                tests=run_tests(stage,run_id,n,original)
                current_files=files(stage)
                for fresh in added(stage,original):
                    protected[fresh]=current_files[fresh]
                passing=all(k in tests and tests[k]["passed"] and
                    tests[k]["tests"]>=v for k,v in MINIMUM.items())
                passing=passing and all(v["passed"] and v["tests"]>0 for v in tests.values())
                reviewed=result_verdict(stage,n)
                clean=(passing and call.returncode==0 and not modified and reviewed)
                fingerprint=audit_scope_fingerprint(stage,original)
                clean_count=record_independent_review(fingerprint,clean,run_id)
                status["scope_fingerprint"]=fingerprint
                status["independent_clean_review_count"]=clean_count
                status["passes"].append({"pass":n,"agent_exit":call.returncode,
                    "modified":modified,"tests":{k:[v["tests"],v["passed"]]
                    for k,v in tests.items()},"reviewed":reviewed,
                    "consecutive_clean":clean_count})
                q.atomic_json(q.RESULTS/(run_id+"-checkpoint.json"),status)
                if clean_count>=2:
                    status["converged_tested_scope"]=True
                    status["stop_reason"]="two_clean_independent_reviews"
                    break
                if call.returncode!=0:
                    status["stop_reason"]="agent_failure"
                    break
                # Spending two further calls without any code change while
                # a known test failure remains cannot make that defect vanish.
                if not passing and not modified:
                    status["stop_reason"]="unresolved_without_patch"
                    break
            else:
                status["stop_reason"]="bounded_pass_limit"
            changed=[p for p in original if q.sha(q.SOURCE/p)!=files(stage).get(p)]
            status["changed_code"]=changed
            status["post"]={k:{"tests":v["tests"],"passed":v["passed"]} for k,v in tests.items()}
            status["new_tests"]=added(stage,original)
            status["source_base_hashes"]={p:q.sha(q.SOURCE/p) for p in changed}
            final_good=all(v["passed"] and v["tests"]>0 for v in tests.values())
            safe_changes=not any(p.get("safety_violations") for p in status["passes"])
            status["carry_forward_allowed"]=bool(changed) and final_good and safe_changes
            status["ready_for_manual_review"]=status["carry_forward_allowed"] and status["converged_tested_scope"]
            if changed and safe_changes:
                diff=[]
                for n in changed:
                    diff.extend(difflib.unified_diff((q.SOURCE/n).read_text().splitlines(keepends=True),
                        (stage/n).read_text().splitlines(keepends=True),
                        fromfile="a/"+n,tofile="b/"+n))
                patch=q.RESULTS/(run_id+"-proposal.patch")
                patch.write_text("".join(diff),encoding="utf-8")
                os.chmod(patch,0o600)
                status["patch_path"]=str(patch)
            status["end_utc"]=q.dt.datetime.now(q.dt.timezone.utc).isoformat()
            q.atomic_json(q.RESULTS/(run_id+"-status.json"),status)
            q.atomic_json(q.RESULTS/"latest.json",status)
            print("QA finished:",status["stop_reason"])
            return 0 if status["converged_tested_scope"] else 2
        except Exception as exc:
            status["stop_reason"]="execution_error"
            status["error"]=type(exc).__name__
            q.atomic_json(q.RESULTS/(run_id+"-status.json"),status)
            return 3

if __name__=="__main__":
    sys.exit(main())