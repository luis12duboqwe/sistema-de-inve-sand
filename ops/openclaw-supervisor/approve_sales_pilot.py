#!/usr/bin/env python3
"""Owner-approved offline SoftMobile sales pilot bundle; NEVER activates chat or WAHA.

Requires evidence of the exact SHA reviewed across all synthetic suites.
The original live Ruby remains pinned so QA/autofix jobs continue safely.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,sys,tempfile
from pathlib import Path

LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
BASE_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
SHA="a4ca83e5d83244eb8552c67ad55d291eb601440b9c94c4bd614cd7d28365c06d"
SRC=Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill/candidates/deep-review-a4ca83e5d83244eb.rb")
REPORT=Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill/deep-lab-latest.json")
DIR=Path("/opt/softmobile-waha-test/approved-sales-pilot")
DEST=DIR/("sales-pilot-"+SHA[:16]+".rb")
MANIFEST=DIR/"approval.json"
IMAGE="chatwoot/chatwoot:v4.18.0-ce"

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def read_report():
    d=json.loads(REPORT.read_text())
    need={"mode":"REPLICA_SALES_DEEP_REVIEW",
          "status":"qa_passed_manual_review_required",
          "scope":"sales_only",
          "source_sha256":BASE_SHA,
          "candidate_sha256":SHA,
          "candidate_file":str(SRC),
          "deep_dialogues":10,
          "deep_buyer_turns":150,
          "deep_checks_passed":32,
          "deep_checks_total":32,
          "new_heldout_passed":13,
          "new_heldout_total":13,
          "commercial_72_passed":72,
          "paraphrases_18_passed":18,
          "rotating_6_passed":6,
          "adversarial_11_passed":11,
          "fictitious_checkout_72_passed":72,
          "additional_22_passed":22,
          "unit_tests_passed":68,
          "synthetic_only":True,
          "independent_real_world_qa_passed":False,
          "commercial_data_verified":False,
          "public_release_permitted":False,
          "candidate_deployed":False,
          "production_modified":False,
          "public_messages_sent":0}
    for key,value in need.items():
        if d.get(key)!=value or type(d.get(key))!=type(value):
            raise RuntimeError("approval QA gate failed: "+key)
    stamped=datetime.fromisoformat(d["at"].replace("Z","+00:00"))
    if not 0<=(datetime.now(timezone.utc)-stamped).total_seconds()<=24*3600:
        raise RuntimeError("stale candidate QA")
    if SRC.is_symlink() or LIVE.is_symlink() or digest(SRC)!=SHA or digest(LIVE)!=BASE_SHA:
        raise RuntimeError("candidate or active source changed")
    old=LIVE.read_text(encoding="utf-8")
    new=SRC.read_text(encoding="utf-8")
    for marker in ("INBOX_ID = 2","PILOT_CONVERSATION_ID = 3","AUTO_REPLY_LIMIT = 1"):
        if old.count(marker)!=1 or new.count(marker)!=1:
            raise RuntimeError("pilot guard changed: "+marker)
    suffix="\nif ENV['SM_MODE']=='test'\n"
    if old.count(suffix)!=1 or new.count(suffix)!=1:
        raise RuntimeError("runtime boundary changed")
    # No new Chatwoot sender, catalog bridge or public flow permitted.
    if old.split(suffix,1)[1]!=new.split(suffix,1)[1]:
        raise RuntimeError("public runner runtime flow differs")
    if new.count("REPLICA_DEEP_SALES_V1_BEGIN")!=1 or new.count("REPLICA_DEEP_SALES_V1_END")!=1:
        raise RuntimeError("deep reviewed changes absent")
    return d

def no_public_timers():
    units=["softmobile-waha-catalog-notes.timer",
           "softmobile-ai-agent-public-pilot.timer",
           "softmobile-combined-pilot-promotion.timer"]
    for unit in units:
        rc=subprocess.run(["systemctl","is-active","--quiet",unit],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        if rc.returncode==0:
            raise RuntimeError("public integration timer is active: "+unit)

def sandbox_syntax(src):
    cmd=["docker","run","--rm","-i","--pull","never",
        "--network","none","--read-only","--cap-drop","ALL",
        "--security-opt","no-new-privileges","--pids-limit","48",
        "--memory","200m","--cpus","0.5","--user","65534:65534",
        "--tmpfs","/tmp:rw,noexec,nosuid,size=8m","--env","HOME=/tmp",
        "--entrypoint","ruby",IMAGE,"-c","-"]
    with src.open("rb") as handle:
        ret=subprocess.run(cmd,stdin=handle,text=True,capture_output=True,
                           timeout=45,check=False)
    if ret.returncode!=0 or "Syntax OK" not in ret.stdout:
        raise RuntimeError("networkless Ruby syntax QA failed")

def atomic_save(p,data):
    fd,name=tempfile.mkstemp(prefix=".approved-",dir=p.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as h:
            h.write(data);h.flush();os.fsync(h.fileno())
        os.replace(name,p)
    finally:
        if os.path.exists(name):os.unlink(name)

def approve():
    read_report()
    no_public_timers()
    sandbox_syntax(SRC)
    DIR.mkdir(mode=0o700,parents=True,exist_ok=True)
    if DIR.is_symlink():
        raise RuntimeError("unsafe release folder")
    if DEST.is_symlink() or MANIFEST.is_symlink():
        raise RuntimeError("unsafe release target")
    if DEST.exists() and digest(DEST)!=SHA:
        raise RuntimeError("release target collision")
    atomic_save(DEST,SRC.read_bytes())
    if digest(DEST)!=SHA:
        raise RuntimeError("promoted candidate hash mismatch")
    sandbox_syntax(DEST)
    # Recheck origin and public timers before returning success.
    read_report()
    no_public_timers()
    decision={
      "schema_version":1,
      "at":datetime.now(timezone.utc).isoformat(),
      "scope":"sales_only",
      "owner_authorized_internal_pilot":True,
      "approved_for":"offline_internal_pilot_only",
      "status":"approved_candidate_bundle_staged",
      "source_sha256":BASE_SHA,
      "candidate_sha256":SHA,
      "approved_ruby_file":str(DEST),
      "lab_qa_complete":True,
      "manual_public_release_approved":False,
      "public_channel_enabled":False,
      "chatwoot_runner_modified":False,
      "waha_runner_modified":False,
      "live_source_modified":False,
      "public_messages_sent":0,
      "inventory_modified":False,
      "payments_initiated":0,
      "repairs_out_of_scope":True,
      "rollback":"remove approved-sales-pilot bundle; original /opt/softmobile-waha-test/sales-bot-v2.rb remains unchanged"
    }
    atomic_save(MANIFEST,(json.dumps(decision,ensure_ascii=False,indent=2)+"\n").encode())
    return decision

def check():
    d=json.loads(MANIFEST.read_text())
    if d.get("status")!="approved_candidate_bundle_staged" or d.get("candidate_sha256")!=SHA:
        raise RuntimeError("not approved")
    if not DEST.exists() or DEST.is_symlink() or digest(DEST)!=SHA:
        raise RuntimeError("approved release artifact changed")
    read_report()
    no_public_timers()
    sandbox_syntax(DEST)
    return d

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve",action="store_true")
    group.add_argument("--check",action="store_true")
    args=ap.parse_args()
    try:
        outcome=approve() if args.approve else check()
        print(json.dumps({"status":outcome["status"],
            "candidate_sha256":outcome["candidate_sha256"],
            "approved_file":outcome["approved_ruby_file"],
            "public_channel_enabled":False,
            "live_source_modified":False},ensure_ascii=False))
    except Exception as err:
        print(json.dumps({"status":"BLOCKED","reason":str(err)[:150],
            "public_channel_enabled":False}),file=sys.stderr)
        raise SystemExit(2)