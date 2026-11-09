#!/usr/bin/env python3
"""SHA-pinned offline full QA for currently active sales-only Ruby.

Never opens customer channels. This report is not a public release permission.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,os,sys,tempfile,subprocess
import business_policy_full_qa as suite

ROOT=Path("/opt/softmobile-waha-test")
SOURCE=ROOT/"sales-bot-v2.rb"
CANDIDATE_SHA="2c4d6d274402daa34f44f7e669efe9aaf7bc2d01574f5b53505779fb8592c885"
EXPECTED_BUSINESS={
 "knowledge/reglas.md":"723089189e17be625edd17b627fb8e2aa6c07596bf03d493a0144b6937459169",
 "knowledge/catalogo.json":"bf8fef5a14ae4e3b0d77fa838a1ed1eb474b7b38dba586574b6797af5113cf2f",
 "knowledge/softmobile-business.json":"50c46724c180cf47e9f38b947e691eddfb5f46886ccde8fff3c791d03e8f624c"}
OUTPUT=ROOT/"approved-sales-pilot/active-sales-policy-qa.json"
CHECKS=("softmobile-waha-catalog-notes.timer",
        "softmobile-ai-agent-public-pilot.timer",
        "softmobile-combined-pilot-promotion.timer")

def sha(p):return sha256(Path(p).read_bytes()).hexdigest()

def validate_business():
    for name,expected in EXPECTED_BUSINESS.items():
        p=ROOT/name
        if p.is_symlink() or not p.is_file() or sha(p)!=expected:
            raise RuntimeError("business source revision requires re-audit")
    rules=json.loads((ROOT/"knowledge/softmobile-business.json").read_text())
    catalog=json.loads((ROOT/"knowledge/catalogo.json").read_text())
    if (rules.get("brand")!="SoftMobile" or
        rules.get("reservation_delivery",{}).get("reservations_allowed") is not False
        or len(catalog)!=97):
        raise RuntimeError("commercial rules or catalog changed")

def no_public_timers():
    for unit in CHECKS:
        if subprocess.run(["systemctl","is-active","--quiet",unit],check=False,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
            raise RuntimeError("customer channel unexpectedly active")

def atomic_json(dest,data):
    fd,tmp=tempfile.mkstemp(prefix=".sales-policy-",dir=dest.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def evaluate():
    validate_business()
    no_public_timers()
    if SOURCE.is_symlink() or not SOURCE.is_file() or sha(SOURCE)!=CANDIDATE_SHA:
        raise RuntimeError("active Ruby is not reviewed business-policy version")
    text=SOURCE.read_text(encoding="utf-8")
    if text.count("BUSINESS_PLAYBOOK_20261106_NO_RESERVATIONS_BEGIN")!=1:
        raise RuntimeError("business rules not embedded in active Ruby")
    results=suite.evaluate(text)
    if results.get("passed") is not True or results.get("source_sha256")!=CANDIDATE_SHA:
        raise RuntimeError("live Ruby failed independent policy QA")
    if sha(SOURCE)!=CANDIDATE_SHA:
        raise RuntimeError("active source changed during QA")
    validate_business()
    no_public_timers()
    return {
      "schema_version":1,
      "mode":"ACTIVE_RUBY_SALES_POLICY_20261106",
      "at":datetime.now(timezone.utc).isoformat(),
      "status":"passed_offline_current_source",
      "scope":"sales_only",
      "source_sha256":CANDIDATE_SHA,
      "active_ruby_checked":True,
      "commercial_dialogues_passed":results["policy_72"],
      "historical_nonreserve_dialogues_passed":60,
      "explicit_no_reserve_dialogues_passed":results["policy_reservations_correctly_denied"],
      "nov6_policy_cases_passed":results["new_commercial_policy_20"],
      "nov6_policy_cases_total":results["new_commercial_policy_total"],
      "heldout_passed":results["heldout_policy_passed"],
      "adversarial_passed":results["edge_policy_passed"],
      "rotating_passed":results["rotating_policy_passed"],
      "independent_passed":results["independent_policy_passed"],
      "deep_criteria_passed":results["deep_criteria_policy_passed"],
      "unit_tests_passed":results["unit_tests_passed"],
      "legacy_checkout_simulated_passed":results["fictional_checkout_passed"],
      "real_catalog_prices_or_stock_verified":False,
      "real_customer_conversation_tested":False,
      "production_modified":False,
      "public_messages_sent":0,
      "deployment_permission":False,
      "public_release_permitted":False}

def main():
    try:result=evaluate()
    except Exception as err:
        result={"schema_version":1,"mode":"ACTIVE_RUBY_SALES_POLICY_20261106",
            "at":datetime.now(timezone.utc).isoformat(),
            "status":"blocked","reason":str(err)[:170],
            "public_release_permitted":False,"public_messages_sent":0,
            "production_modified":False}
    atomic_json(OUTPUT,result)
    print(json.dumps({"status":result["status"],
            "source_sha256":result.get("source_sha256"),
            "scenarios":result.get("commercial_dialogues_passed"),
            "reason":result.get("reason"),
            "public_release_permitted":False},ensure_ascii=False))
    return 0 if result["status"]=="passed_offline_current_source" else 2

if __name__=="__main__":
    raise SystemExit(main())