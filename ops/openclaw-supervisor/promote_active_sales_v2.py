#!/usr/bin/env python3
"""Owner-authorized sales-only Ruby migration, full rollback on QA failure.

The public customer channel remains INACTIVE. No messages or payment writes.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,tempfile
from pathlib import Path

ROOT=Path("/opt/softmobile-waha-test")
ORIGINAL=ROOT/"sales-bot-v2.rb"
OLD_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
NEW_SHA="2c4d6d274402daa34f44f7e669efe9aaf7bc2d01574f5b53505779fb8592c885"
OLD_BASE=ROOT/"frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb"
NEW_SOURCE=ROOT/("approved-sales-pilot/candidates/business-policy-"+NEW_SHA[:16]+".rb")
MANIFEST=ROOT/"approved-sales-pilot/active-release-migration.json"
NEW_TIMER="softmobile-active-sales-policy-qa.timer"
STOP_TIMERS=[
 "softmobile-sales-autofix-lab.timer",
 "softmobile-replica-cycle.timer",
 "softmobile-approved-sales-pilot-qa.timer",
 "softmobile-seller-conversation-quality.timer",
 "softmobile-sales-deep-qa.timer",
 "softmobile-sales-conversion.timer",
 "softmobile-openclaw-lab.timer",
]
PUBLIC_TIMERS=[
 "softmobile-waha-catalog-notes.timer",
 "softmobile-ai-agent-public-pilot.timer",
 "softmobile-combined-pilot-promotion.timer",
]
MIGRATIONS={
 "/opt/softmobile-waha-test/laboratorio-ia/build_sales_followup_candidate.py":
  ('BOT=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")',
   'BOT=Path("/opt/softmobile-waha-test/frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb")'),
 "/opt/openclaw-lab/supervisor/replica_cycle.py":
  ('SOURCE = BASE / "sales-bot-v2.rb"',
   'SOURCE = BASE / "frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb"'),
 "/opt/openclaw-lab/supervisor/replica_deep_patch.py":
  ('LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")',
   'LIVE=Path("/opt/softmobile-waha-test/frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb")'),
 "/opt/openclaw-lab/supervisor/approve_sales_pilot.py":
  ('LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")',
   'LIVE=Path("/opt/softmobile-waha-test/frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb")'),
 "/opt/openclaw-lab/supervisor/policy_aligned_sales_build.py":
  ('ACTIVE=ROOT/"sales-bot-v2.rb"',
   'ACTIVE=ROOT/"frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb"'),
 "/opt/openclaw-lab/supervisor/patch_source_compat.py":
  ('KNOWN_SHA="'+OLD_SHA+'"','KNOWN_SHA="'+NEW_SHA+'"'),
}
def digest(raw):return sha256(raw).hexdigest()
def unit(name,verb,check=True):
    res=subprocess.run(["systemctl",verb,name],text=True,capture_output=True,check=False,timeout=40)
    if check and res.returncode:
        raise RuntimeError("systemctl "+verb+" failed: "+name+":"+res.stderr[-100:])
    return res.returncode
def atomic(p,blob):
    fd,tmp=tempfile.mkstemp(prefix=".sm-promotion-",dir=p.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as handle:
            handle.write(blob);handle.flush();os.fsync(handle.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def safe_public():
    for n in PUBLIC_TIMERS:
        if unit(n,"is-active",check=False)==0:
            raise RuntimeError("public service active: "+n)
    for name in ("softmobile-waha-catalog-notes.service",
                 "softmobile-ai-agent-public-pilot.service"):
        if unit(name,"is-active",check=False)==0:
            raise RuntimeError("public service running: "+name)
def migrate():
    safe_public()
    if ORIGINAL.is_symlink() or NEW_SOURCE.is_symlink():
        raise RuntimeError("active or proposed Ruby source is a link")
    original=ORIGINAL.read_bytes()
    proposed=NEW_SOURCE.read_bytes()
    if digest(original)!=OLD_SHA or digest(proposed)!=NEW_SHA:
        raise RuntimeError("reviewed Ruby source SHA mismatch")
    report=json.loads((ROOT/"approved-sales-pilot/candidates/business-policy-full-qa.json").read_text())
    if (report.get("source_sha256")!=NEW_SHA or report.get("passed") is not True or
        report.get("policy_72")!=72 or report.get("new_commercial_policy_20")!=20 or
        report.get("independent_policy_passed")!=22 or
        report.get("deep_criteria_policy_passed")!=32 or
        report.get("failed_case_ids")!=[] or
        report.get("production_modified") is not False):
        raise RuntimeError("new Ruby QA evidence incomplete")
    # No active service can process private test messages while promoting.
    for timer in STOP_TIMERS:
        service=timer[:-6]+".service"
        if unit(service,"is-active",check=False)==0:
            raise RuntimeError("concurrent lab service active: "+service)
    orig_scripts={Path(p):Path(p).read_bytes() for p in MIGRATIONS}
    revisions={}
    for path,(old,new) in MIGRATIONS.items():
        f=Path(path)
        s=orig_scripts[f].decode("utf-8")
        if s.count(old)!=1:
            raise RuntimeError("migration anchor no longer unique: "+path)
        revisions[f]=s.replace(old,new,1).encode()
    old_enabled={n:unit(n,"is-enabled",check=False)==0 for n in STOP_TIMERS}
    old_active={n:unit(n,"is-active",check=False)==0 for n in STOP_TIMERS}
    backup=ROOT/"approved-sales-pilot/migrations"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True,mode=0o700,exist_ok=False)
    for i,(path,data) in enumerate(orig_scripts.items()):
        atomic(backup/(f"{i:02d}-{path.name}"),data)
    original_backup=backup/"original-sales-bot-v2.rb"
    atomic(original_backup,original)
    OLD_BASE.parent.mkdir(mode=0o700,exist_ok=True)
    if OLD_BASE.is_symlink() or (OLD_BASE.exists() and digest(OLD_BASE.read_bytes())!=OLD_SHA):
        raise RuntimeError("frozen source collision")
    atomic(OLD_BASE,original)
    changed=[]
    try:
        for timer in STOP_TIMERS:
            if old_active[timer]:
                unit(timer,"stop")
        safe_public()
        for f,data in revisions.items():
            atomic(f,data)
            changed.append(f)
        # The only active-code change is this verified atomic replacement.
        atomic(ORIGINAL,proposed)
        if digest(ORIGINAL.read_bytes())!=NEW_SHA:
            raise RuntimeError("active Ruby readback mismatch")
        # Old diff/Replica QA remain tied to the frozen historical Ruby.
        import sys
        sys.path.insert(0,"/opt/openclaw-lab/supervisor")
        import approve_sales_pilot,patch_source_compat,replica_cycle
        if (digest(approve_sales_pilot.LIVE.read_bytes())!=OLD_SHA or
            digest(replica_cycle.SOURCE.read_bytes())!=OLD_SHA or
            not patch_source_compat.compatible(ORIGINAL.read_text())):
            raise RuntimeError("migrated review/compat sources do not match")
        subprocess.run(["systemctl","daemon-reload"],check=True,timeout=15)
        safe_public()
        unit("softmobile-active-sales-policy-qa.service","start")
        proof=json.loads((ROOT/"approved-sales-pilot/active-sales-policy-qa.json").read_text())
        if (proof.get("status")!="passed_offline_current_source" or
            proof.get("source_sha256")!=NEW_SHA or
            proof.get("commercial_dialogues_passed")!=72 or
            proof.get("public_release_permitted") is not False):
            raise RuntimeError("active QA rejected policy-aligned Ruby")
        safe_public()
        # Resume previously enabled legacy offline QA on its own frozen baseline.
        for timer in STOP_TIMERS:
            if timer in ("softmobile-seller-conversation-quality.timer",
                         "softmobile-sales-deep-qa.timer"):
                continue # replaced by current source policy QA
            if old_active[timer]:unit(timer,"start")
        unit(NEW_TIMER,"enable")
        unit(NEW_TIMER,"start")
        manifest={
         "status":"active_sales_ruby_migrated_offline_only",
         "at":datetime.now(timezone.utc).isoformat(),
         "source_sha256_before":OLD_SHA,
         "active_source_sha256_after":NEW_SHA,
         "legacy_baseline":str(OLD_BASE),
         "original_backup":str(original_backup),
         "backup_dir":str(backup),
         "legacy_offline_timers_resumed":[n for n in STOP_TIMERS if old_active[n] and n not in (
              "softmobile-seller-conversation-quality.timer","softmobile-sales-deep-qa.timer")],
         "legacy_qa_timers_disabled":["softmobile-seller-conversation-quality.timer","softmobile-sales-deep-qa.timer"],
         "current_policy_qa_timer":NEW_TIMER,
         "owner_authorized_internal_sales_integration":True,
         "public_chat_enabled":False,
         "public_messages_sent":0,"real_sales_created":0,
         "stock_modified":False,"payments_initiated":0,
         "customer_release_authorized":False,
         "rollback_requires":"restore original Ruby from original_backup and six patched scripts from backup_dir, then stop new timer and restore old timers",
         "production_ruby_file_modified":True}
        atomic(MANIFEST,(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode())
        return manifest
    except Exception as err:
        # Fail-closed rollback code and source, leave public timers OFF.
        for f in reversed(changed):
            atomic(f,orig_scripts[f])
        atomic(ORIGINAL,original)
        try:
            unit(NEW_TIMER,"stop",check=False)
            subprocess.run(["systemctl","daemon-reload"],check=False,timeout=15)
            for timer in STOP_TIMERS:
                if old_active[timer]:
                    unit(timer,"start",check=False)
        except Exception:
            pass
        atomic(backup/"ROLLBACK_REASON.txt",str(err).encode())
        raise

if __name__=="__main__":
    try:
        out=migrate()
        print(json.dumps({k:out.get(k) for k in (
            "status","source_sha256_before","active_source_sha256_after",
            "current_policy_qa_timer","public_chat_enabled","production_ruby_file_modified")},ensure_ascii=False))
    except Exception as err:
        print("MIGRATION_ABORTED_OR_ROLLED_BACK:",type(err).__name__,str(err)[:175])
        raise SystemExit(2)