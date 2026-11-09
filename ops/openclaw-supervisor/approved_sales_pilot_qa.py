#!/usr/bin/env python3
"""Periodic full offline QA of the owner-approved SHA-pinned Ruby sales pilot.

Only the approved private bundle is read. No Chatwoot, WAHA, ERP or real user data.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json,os,sys,tempfile
from pathlib import Path

import approve_sales_pilot as approval
import replica_qa_probe as baseline
import replica_deep_heldout as additions
import independent_seller_qa as independent

LAB=Path("/opt/softmobile-waha-test/laboratorio-ia")
sys.path.insert(0,str(LAB))
from deep_sales_dialogue_lab import run as dialogue_run
from deep_sales_quality_gate import run as quality_run

OUT=approval.DIR/"approved-pilot-qa.json"

def atomically_record(report):
    data=(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    fd,name=tempfile.mkstemp(dir=OUT.parent,prefix=".qa-")
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as h:
            h.write(data);h.flush();os.fsync(h.fileno())
        os.replace(name,OUT)
    finally:
        if os.path.exists(name): os.unlink(name)

def run():
    approved=approval.check()
    source=approval.DEST.read_text(encoding="utf-8")
    if sha256(source.encode()).hexdigest()!=approval.SHA:
        raise RuntimeError("approved Ruby differs from authorized SHA")
    conversation=dialogue_run(source)
    deep=quality_run(conversation)
    held=additions.evaluate(source)
    extra=independent.evaluate(source)
    regression=baseline.evaluate(source)
    if not (deep.get("source_sha256")==approval.SHA and
        conversation.get("source_sha256")==approval.SHA and
        conversation.get("turn_count")==150 and
        conversation.get("public_messages_sent")==0 and
        conversation.get("production_modified") is False and
        deep.get("checks")==32 and deep.get("passed")==32 and deep.get("failed")==0 and
        held.get("source_sha256")==approval.SHA and
        held.get("scenarios")==13 and held.get("passed")==13 and held.get("failed")==[] and
        extra.get("sha256")==approval.SHA and extra.get("total")==22 and extra.get("passed")==22 and
        regression.get("source_sha256")==approval.SHA and regression.get("passed") is True):
        raise RuntimeError("reviewed-sales test or safety rule did not pass")
    approval.check()
    return {"schema_version":1,
        "mode":"APPROVED_SALES_PILOT_OFFLINE_REGRESSION",
        "at":datetime.now(timezone.utc).isoformat(),
        "status":"passed_internal_pilot_qa",
        "candidate_sha256":approval.SHA,
        "approved_bundle":str(approval.DEST),
        "deep_dialogues":10,"deep_turns":150,
        "deep_criteria_passed":32,
        "heldout_new_passed":13,
        "extra_independent_passed":22,
        "commercial_dialogues_passed":regression["dialogue"]["passed"],
        "paraphrases_passed":regression["heldout"]["passed"],
        "adversarial_passed":regression["adversarial"]["passed"],
        "rotating_passed":regression["rotating"]["passed"],
        "fictional_checkout_passed":regression["checkout"]["passed"],
        "unit_tests_passed":regression["unit_tests_passed"],
        "owner_approved_internal_pilot":True,
        "public_release_permitted":False,"public_messages_sent":0,
        "real_orders":0,"payments_initiated":0,
        "inventory_modified":False,"production_modified":False}

def main():
    try:
        report=run()
    except Exception as exc:
        report={"schema_version":1,"mode":"APPROVED_SALES_PILOT_OFFLINE_REGRESSION",
            "at":datetime.now(timezone.utc).isoformat(),"status":"blocked",
            "reason":str(exc)[:170],"public_release_permitted":False,
            "public_messages_sent":0,"production_modified":False}
    atomically_record(report)
    print(json.dumps({k:report.get(k) for k in
      ("status","candidate_sha256","deep_criteria_passed","heldout_new_passed",
       "commercial_dialogues_passed","unit_tests_passed","reason",
       "public_release_permitted")},ensure_ascii=False))
    return 0 if report["status"]=="passed_internal_pilot_qa" else 2

if __name__=="__main__":
    raise SystemExit(main())