#!/usr/bin/env python3
"""OpenClaw <-> SoftMobile quality lab: quarantined proposal workflow.
No live writes to SoftMobile, Chatwoot, WAHA, inventory, or systemd deployment timers.
"""
import datetime as dt
import difflib
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import traceback

BASE = pathlib.Path("/opt/openclaw-lab")
SOURCE = pathlib.Path("/opt/softmobile-waha-test")
SNAP = BASE / "workspace" / "lab-runs"
RESULTS = BASE / "results" / "lab-cycles"
IMAGE = "ghcr.io/openclaw/openclaw:latest"
UID = 1000
GID = 1000
SUITES = [
    ("sales", "laboratorio-ia", [
        "test_sales_ai_agent", "test_sales_ai_photo_adapter",
        "test_business_playbook", "test_pilot_memory", "test_dialogue_slots",
        "test_variant_preference", "test_staff_ai_handoff", "test_lab_acceptance",
        "test_provider_cooldown", "test_sales_context", "test_issue_triage",
        "test_synthetic_lab", "test_autonomous_learning"
    ]),
    ("photos", "staff-bridge", ["test_openclaw_workflow_regressions"]),
    ("photo_ack", "staff-bridge", ["test_photo_ack_polish"])
]
# Reviewed Nov 2026: old test_dialogos_aprobados asserts FIVE unsafe promises
# (prices from an unverified reference catalog and fake staff handoffs).
# The versioned contract inherits its other 31 tests unchanged and replaces
# exactly those five with safety-first assertions. The legacy file is retained.
SUITES.append(("commercial", "laboratorio-ia", ["test_commercial_policy_contract","test_reglas_comerciales","test_commercial_operations"]))
LEGACY_COMMERCIAL_TEST_SHA = "a6e90d05d9452c559eefeb534beb4b3bdf13e828563e4df331362432f650d20f"
POLICY_CONTRACT = BASE / "integration" / "policy_contracts" / "test_commercial_policy_contract.py"
METRIC_FILES = {
    "lab-acceptance-report.json": ["at", "weighted_score_percent", "complete",
        "unresolved_qa_signals", "cannot_authorize_public_rollout", "real_inventory_verified"],
    "synthetic-lab-summary.json": ["at", "pilot_only", "total_simulations", "simulated",
        "unverified_issues_stored", "accepted_ai_scenarios", "autonomous_code_changes"],
    "issue-triage-report.json": ["at", "total_records", "distinct_issue_ids",
        "duplicate_conversation_fingerprints", "promoted_or_proven_by_ai_alone"],
    "agent-dialogue-lab-report.json": ["at", "scenarios_run", "deterministic_passed",
        "public_messages_sent", "automatic_code_patches", "deployment_permitted"],
    "ai-agent-migration-status.json": ["at", "status", "tests_run", "tests_passed",
        "real_stock_verified", "live_language_understanding_unverified",
        "agent_public_whatsapp_enabled", "production_deployment_allowed"],
    "interactive-lab-summary.json": ["at", "buyer_turns", "grading_available", "issue_observed"],
    "repair-lab-summary.json": ["at", "status", "promoted", "raw_model_code_executed"]
}

def stamp():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def atomic_json(p, data):
    tmp = p.with_suffix(p.suffix+".new")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    os.chmod(tmp,0o600)
    tmp.replace(p)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def copy(p, dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(p,dst)
    os.chmod(dst,0o644)
    os.chown(dst,UID,GID)

def prepare(stage):
    stage.mkdir(parents=True, exist_ok=False)
    os.chown(stage, UID, GID)
    sources = []
    for p in sorted((SOURCE/"laboratorio-ia").glob("*.py")):
        if p.name in ("configurar_clave_groq.py","test_configurar_clave_groq.py"):
            continue
        if p.is_symlink(): continue
        rel=p.relative_to(SOURCE); copy(p,stage/rel); sources.append(str(rel))
    # Refuse silent test-contract drift; do not rewrite the historical tests.
    legacy=SOURCE/"laboratorio-ia"/"test_dialogos_aprobados.py"
    if sha(legacy)!=LEGACY_COMMERCIAL_TEST_SHA or POLICY_CONTRACT.is_symlink() or not POLICY_CONTRACT.is_file():
        raise RuntimeError("commercial_contract_requires_engineering_reaudit")
    copy(POLICY_CONTRACT,stage/"laboratorio-ia"/POLICY_CONTRACT.name)
    for name in ("workflow.py","ack_customers.py","test_photo_ack_polish.py"):
        p=SOURCE/"staff-bridge"/name
        copy(p,stage/p.relative_to(SOURCE)); sources.append(str(p.relative_to(SOURCE)))
    # Disconnected stub; regression fixtures intercept this function, and the
    # sandbox cannot load Chatwoot or contact customers.
    stub=stage/"staff-bridge"/"scan_chatwoot.py"
    stub.write_text("def rails_runner(*args,**kwargs):\n    raise RuntimeError('offline_only')\n",encoding="utf-8")
    os.chown(stub,UID,GID);os.chmod(stub,0o644)
    trusted=BASE/"workspace"/"softmobile-bot-snapshot"/"staff-bridge"/"test_openclaw_workflow_regressions.py"
    copy(trusted,stage/"staff-bridge"/trusted.name)
    (stage/"laboratorio-ia"/"configurar_clave_groq.py").write_text(
        '''"""Offline safe credential placeholder: no credentials are installed."""
from pathlib import Path
TARGET=Path("/nonexistent/no-credentials")
def stored_key(target=TARGET): return None
def save_key(*a,**kw): raise RuntimeError("No secret access in QA lab")
def verify(*a,**kw): raise RuntimeError("No secret access in QA lab")
''', encoding="utf-8")
    for rel in (
        "laboratorio-ia/quality/reference-catalog.json",
        "knowledge/customer-automation-matrix.json",
        "knowledge/softmobile-business.json",
        "knowledge/catalogo.json",
        "knowledge/reglas.md"
    ):
        src=SOURCE/rel
        if src.exists() and src.is_file() and not src.is_symlink(): copy(src,stage/rel)
    # Only numerical/boolean and bounded status/time metadata; never raw transcripts.
    metrics={}
    for name,keys in METRIC_FILES.items():
        p=SOURCE/"laboratorio-ia"/"quality"/name
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(d,dict): continue
            metrics[name]={k:v for k in keys if (v:=d.get(k)) is not None and
                           (type(v) in (bool,int,float) or (isinstance(v,str) and len(v)<=70))}
        except (OSError,ValueError): continue
    (stage/"LAB_FEED.json").write_text(json.dumps({
        "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source":"metadata aggregates of existing lab, not customer conversations",
        "metric_reports":metrics},ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    (stage/"AGENTS.md").write_text("""# SOFTMOBILE — ISOLATED AUTONOMOUS QA
You are operating ONLY on this sanitized COPY. This directory has no production database, channel access, secrets, phone numbers or staff registry.
Never access outside this workspace, live systems or customer messages. Never deploy, trigger systemd, WhatsApp, Chatwoot, WAHA, ERP, n8n or payment workflows.
LAB_FEED.json contains aggregate metrics, NOT proof of live sales readiness. Reference catalog is NOT verified stock, color or price information.
Never invent facts or claim tests passed unless output actually proves it.
You may edit copies of implementation *.py inside laboratorio-ia and staff-bridge/workflow.py ONLY.
Do NOT edit existing tests, fixtures, AGENTS.md, LAB_FEED.json or safety controls. Add a regression test only with a NEW test_*.py filename.
Avoid unnecessary edits; if evidence is insufficient, provide findings only. No model-driven production changes or remote tool/API invocations.
""",encoding="utf-8")
    (stage/"TASK.md").write_text("""For the commercial suite, read knowledge/reglas.md and knowledge/catalogo.json. Approved list prices may be quoted; availability still requires staff confirmation. Analyze the existing SoftMobile laboratory using LAB_FEED.json, the synthetic inventory business rules and offline test failures (BASELINE_TEST_RESULTS.txt).
Priority: customer intent/context, simultaneous photo tickets, cancellation races, stock/price hallucinations, and laboratory judge failures.
Complete ONE autonomous QA cycle. Review source and regressions, find grounded defects and produce minimal code changes ONLY in this isolated copy, plus new tests if needed.
A known regression suite for photo workflow is provided; if failing, try to fix it without breaking passing suites.
Create QA_RESULT.md with: issues verified vs suspected; patches; regressions executed; business risks and whether metrics reflect live readiness (they do not).
Do not copy raw customer content; do not run anything that sends a WhatsApp or edits real systems. No deployment. Keep final reply short.
""",encoding="utf-8")
    for p in stage.rglob("*"):
        if p.is_dir():
            os.chown(p,UID,GID)
    for p in (stage/"laboratorio-ia"/"configurar_clave_groq.py", stage/"LAB_FEED.json",stage/"TASK.md",stage/"AGENTS.md"):
        os.chown(p,UID,GID)
        os.chmod(p,0o644)
    # Carry a previously verified proposal ONLY within sandbox when original source
    # hashes are unchanged. This avoids re-spending a model turn fixing the same
    # pending issue, and NEVER modifies the live bot.
    carried=[]
    previous=RESULTS/"latest.json"
    try:
        last=json.loads(previous.read_text())
        # A failed agent run must not erase the last validated pending patch.
        # Search historical verified runs, newest first, if latest cannot carry.
        if not (last.get("ready_for_manual_review") or last.get("carry_forward_allowed")):
            for saved in sorted(RESULTS.glob("*-status.json"),reverse=True):
                candidate=json.loads(saved.read_text(encoding="utf-8"))
                if candidate.get("ready_for_manual_review") or (candidate.get("carry_forward_allowed") and candidate.get("post")):
                    last=candidate
                    break
        prior=pathlib.Path(last.get("stage","")).resolve()
        changed=last.get("changed_code",[])
        originals=last.get("source_base_hashes",{})
        verified_post=last.get("post",{})
        post_ok=isinstance(verified_post,dict) and bool(verified_post) and all(
            isinstance(v,dict) and v.get("passed") is True and
            int(v.get("tests",0))>0 for v in verified_post.values())
        accepted=last.get("ready_for_manual_review") is True or (
            last.get("mode")=="offline_reaudit" and
            last.get("carry_forward_allowed") is True and post_ok and
            not any(p.get("safety_violations") for p in last.get("passes",[])))
        valid=(accepted and changed and prior.is_relative_to(SNAP.resolve()) and
               all(n in originals and (SOURCE/n).is_file() and
                   (prior/n).is_file() and
                   sha(SOURCE/n) in (originals[n],sha(prior/n)) for n in changed))
        if valid:
            for n in changed:
                # Source already equals the approved isolated proposal? Don't
                # revert a deployed file; carry only still-pending patches.
                if sha(SOURCE/n)==originals[n] and (n=="staff-bridge/workflow.py" or
                   (n.startswith("laboratorio-ia/") and n.endswith(".py") and
                    not pathlib.Path(n).name.startswith("test_"))):
                    copy(prior/n,stage/n)
                    carried.append(n)
            for n in last.get("new_tests",[]):
                f=pathlib.Path(n)
                if len(f.parts)==2 and f.parts[0] in ("laboratorio-ia","staff-bridge") and re.fullmatch(r"test_[A-Za-z0-9_]+\.py",f.name) and (prior/n).is_file():
                    copy(prior/n,stage/n)
    except (OSError,ValueError,TypeError,KeyError):
        pass
    if carried:
        (stage/"CARRIED_PENDING_PATCH.md").write_text(
            "Pending previously tested patch copied into this isolated lab run: "+
            ", ".join(carried)+
            ". NOT deployed in SoftMobile. Source unchanged; revalidate before any future deployment.\\n",
            encoding="utf-8")
        os.chown(stage/"CARRIED_PENDING_PATCH.md",UID,GID)
    # Pass only aggregate, privacy-filtered pilot QA signals into OpenClaw.
    feedback=BASE/"results"/"pilot-feedback-aggregate.json"
    if feedback.is_file():
        try:
            d=json.loads(feedback.read_text(encoding="utf-8"))
            if d.get("raw_customer_content_stored") is False:
                data={k:d.get(k) for k in ("at","status","evaluated",
                    "privacy_filtered","classifications","post_fix_start_utc",
                    "post_fix_evaluated","post_fix_classifications","post_fix_status",
                    "human_confirmation_required","provider_health")}
                output=stage/"PILOT_FEEDBACK.json"
                output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                os.chown(output,UID,GID)
        except (OSError,ValueError,TypeError):
            pass
    return sources,carried

def test(stage, label, out, extra_tests=None):
    stage_tmp=RESULTS/(out.stem+"-scratch")
    if stage_tmp.exists(): shutil.rmtree(stage_tmp)
    shutil.copytree(stage,stage_tmp)
    # QA container can only write to disposable sandbox (never original)
    for root,dirs,files in os.walk(stage_tmp):
        os.chown(root,UID,GID)
        for n in files: os.chown(os.path.join(root,n),UID,GID)
    summaries={}
    suites=[(name,workdir,list(tests)) for name,workdir,tests in SUITES]
    for rel in (extra_tests or []):
        f=pathlib.Path(rel)
        if len(f.parts)!=2 or f.parts[0] not in ("laboratorio-ia","staff-bridge") or not re.fullmatch(r"test_[A-Za-z0-9_]+\.py",f.name):
            raise ValueError("Unexpected new test file: "+str(rel))
        suites.append(("new-"+f.stem,f.parts[0],[f.stem]))
    for name,workdir,tests in suites:
        cmd=["docker","run","--rm","--network","none","--read-only","--cap-drop","ALL",
             "--security-opt","no-new-privileges","--pids-limit","96","--memory","768m","--cpus","1.5",
             "--user","1000:1000","--mount",f"type=bind,src={stage_tmp},dst=/review",
             "--tmpfs","/tmp:rw,nosuid,size=64m",
             "--workdir",f"/review/{workdir}",
             "--env","PYTHONDONTWRITEBYTECODE=1",
             "--env","PYTHONPATH=/review/staff-bridge:/review/laboratorio-ia",
             "--entrypoint","/usr/bin/python3",IMAGE,
             "-m","unittest","-q",*tests]
        try:
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=120,check=False)
            content=(proc.stdout or "")+"\n"+(proc.stderr or "")
            match=re.search(r"Ran (\d+) tests?",content)
            summaries[name]={"returncode":proc.returncode,"tests":int(match.group(1)) if match else 0,
                "passed":proc.returncode==0,"tail":content[-3200:]}
        except (subprocess.TimeoutExpired,OSError) as exc:
            summaries[name]={"returncode":-1,"tests":0,"passed":False,"tail":str(exc)[:200]}
    atomic_json(out,summaries)
    shutil.rmtree(stage_tmp)
    return summaries

def main():
    (BASE/"integration").mkdir(parents=True,exist_ok=True)
    with (BASE/"integration"/"cycle.lock").open("a+") as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print("SKIPPED: prior QA cycle running",flush=True); return 0
        SNAP.mkdir(parents=True,exist_ok=True)
        RESULTS.mkdir(parents=True,exist_ok=True)
        run_id=stamp()
        stage=SNAP/run_id
        status={"run_id":run_id,"stage":str(stage),"start_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
                "mode":"offline_copy_only","production_changed":False,"agent_status":"not_started"}
        try:
            files,carried=prepare(stage)
            status["carried_proposals"]=carried
            before={n:sha(stage/n) for n in files}
            protected={str(p.relative_to(stage)):sha(p) for p in stage.rglob("*")
                       if p.is_file() and (p.name.startswith("test_") or p.suffix==".json" or p.name in ("AGENTS.md","TASK.md"))}
            base=test(stage,"baseline",RESULTS/(run_id+"-baseline.json"))
            status["baseline"]={k:{"tests":v["tests"],"passed":v["passed"]} for k,v in base.items()}
            text_lines=["# Baseline results","Offline Docker without network.",
                        "These are PRE-CORRECTION tests. Do not assert all passed."]
            for n,r in base.items():
                text_lines.append(f"\n## {n}: ran={r['tests']} passed={r['passed']}\n{r['tail'][-2200:]}")
            (stage/"BASELINE_TEST_RESULTS.txt").write_text("\n".join(text_lines)+"\n",encoding="utf-8")
            os.chown(stage/"BASELINE_TEST_RESULTS.txt",UID,GID)
            prompt=f"Lee AGENTS.md, TASK.md, LAB_FEED.json y BASELINE_TEST_RESULTS.txt dentro de /home/node/.openclaw/workspace/lab-runs/{run_id}. Ejecuta la auditoría y corregí SOLO esta copia. Escribe QA_RESULT.md en esa misma carpeta. Sin despliegue ni conversaciones reales."
            proc=subprocess.run(["docker","exec","openclaw-lab","node","dist/index.js","agent",
              "--message",prompt,"--session-id","labcycle-"+run_id,
              "--thinking","low","--timeout","310"],capture_output=True,text=True,timeout=370,check=False)
            status["agent_status"]="completed" if proc.returncode==0 else "failed"
            status["agent_exit"]=proc.returncode
            (RESULTS/(run_id+"-agent.log")).write_text(((proc.stdout or "")+"\n"+(proc.stderr or ""))[-6000:],encoding="utf-8")
            after={n:sha(stage/n) for n in files}
            changed=[n for n in files if before[n]!=after[n]]
            newtests=sorted(str(p.relative_to(stage)) for p in stage.glob("**/test_*.py") if str(p.relative_to(stage)) not in files and p.name not in ("test_openclaw_workflow_regressions.py","test_commercial_policy_contract.py"))
            bad=[n for n in changed if n.startswith("laboratorio-ia/test_") or (n not in ["staff-bridge/workflow.py"] and not (n.startswith("laboratorio-ia/") and n.endswith(".py")))]
            bad += [n for n,h in protected.items() if not (stage/n).is_file() or sha(stage/n)!=h]
            unsafe_links=[str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_symlink()]
            bad += unsafe_links
            if unsafe_links: raise RuntimeError("Agent created a symlink: "+str(unsafe_links[:4]))
            status["changed_code"]=changed
            status["source_base_hashes"]={n:sha(SOURCE/n) for n in changed}
            status["test_or_policy_tampering"]=bad
            status["new_tests"]=newtests
            post=test(stage,"post",RESULTS/(run_id+"-post.json"), extra_tests=newtests)
            status["post"]={k:{"tests":v["tests"],"passed":v["passed"]} for k,v in post.items()}
            status["ready_for_manual_review"] = bool(changed) and not bad and all(v["passed"] for v in post.values()) and proc.returncode==0
            if changed:
                lines=[]
                for n in changed:
                    original=(SOURCE/n).read_text(encoding="utf-8").splitlines(keepends=True)
                    updated=(stage/n).read_text(encoding="utf-8").splitlines(keepends=True)
                    lines += list(difflib.unified_diff(original,updated,fromfile="a/"+n,tofile="b/"+n))
                patch=RESULTS/(run_id+"-proposal.patch")
                patch.write_text("".join(lines),encoding="utf-8")
                os.chmod(patch,0o600)
                status["patch_path"]=str(patch)
            status["end_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
            atomic_json(RESULTS/(run_id+"-status.json"),status)
            atomic_json(RESULTS/"latest.json",status)
            print(json.dumps({k:status[k] for k in
                ("run_id","agent_status","baseline","post","changed_code","ready_for_manual_review","production_changed")},
                ensure_ascii=False),flush=True)
            return 0 if proc.returncode==0 and not bad and all(v["passed"] for v in post.values()) else 2
        except Exception as e:
            status["error"]=repr(e)
            status["traceback"]=traceback.format_exc()[-1500:]
            status["end_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
            atomic_json(RESULTS/(run_id+"-status.json"),status)
            atomic_json(RESULTS/"latest.json",status)
            print("LAB CYCLE FAILED:", repr(e),flush=True)
            return 3

if __name__=="__main__":
    sys.exit(main())
