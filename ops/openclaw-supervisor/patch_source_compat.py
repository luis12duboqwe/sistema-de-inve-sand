#!/usr/bin/env python3
"""Pin current pilot Ruby before allowing any model-authored diff to be staged.

This does not call an AI API and never runs, merges or deploys a proposal.
The source guard rejects new code until an engineer explicitly re-audits it.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

from supervisor import OUT,save

BOT=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
KNOWN_SHA="2c4d6d274402daa34f44f7e669efe9aaf7bc2d01574f5b53505779fb8592c885"
SAFETY_ANCHOR=("        choices=color_options(variant_str)\n"
               "        if choices.any?\n"
               "          data[:color_options]=choices\n")
def compatible(source,known_sha=KNOWN_SHA):
    if not isinstance(source,str) or len(source)>250000:
        return False
    if hashlib.sha256(source.encode()).hexdigest()!=known_sha:
        return False
    if source.count("    def context_from(texts)\n")!=1:
        return False
    if source.count(SAFETY_ANCHOR)!=1:
        return False
    for marker in ("PILOT_CONVERSATION_ID = 3","INBOX_ID = 2",
                   "AUTO_REPLY_LIMIT = 1","\nif ENV['SM_MODE']=='test'\n"):
        if marker not in source:return False
    return True

def evidence(src,source_utc):
    good=compatible(src)
    return {"schema_version":1,"mode":"manual_patch_staging_compatibility_only",
       "at":datetime.now(timezone.utc).isoformat(),
       "source_utc":source_utc,
       "ruby_sha256":hashlib.sha256(src.encode()).hexdigest(),
       "matches_independently_reviewed_sha":good,
       "safe_context_anchor_unique":src.count(SAFETY_ANCHOR)==1,
       "proposal_source_compatible":good,
       "max_model_proposal_calls_per_utc_day":4,
       "api_calls_made":0,"proposals_staged":0,
       "patch_timer_approved":False,"deployment_allowed":False,
       "public_messages_sent":0,"production_changed":False}

def main():
    try:
        operator=json.loads((OUT/"OPERATOR.json").read_text())
        director=json.loads((OUT/"DIRECTOR.json").read_text())
        source=operator.get("source_utc")
        if (director.get("source_utc")!=source or
            operator.get("mode")!="internal_actions_only" or
            operator.get("external_actions")!=0 or
            operator.get("public_messages_sent")!=0):
            raise ValueError("unsafe source")
        if BOT.is_symlink():raise ValueError("untrusted bot target")
        import importlib
        sys.path.insert(0,"/opt/softmobile-waha-test/laboratorio-ia")
        pp=importlib.import_module("patch_proposer")
        src=BOT.read_text()
        report=evidence(src,source)
        if report["proposal_source_compatible"]:
            pp.COLOR_ANCHOR=SAFETY_ANCHOR
            _,method,_=pp.method_area(src)
            if method.count(pp.COLOR_ANCHOR)!=1:
                report["proposal_source_compatible"]=False
        save(OUT/"PATCH_COMPAT.json",json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        save(OUT/"PATCH_COMPAT.md",
          "# SoftMobile — source guard de propuestas\n"+
          "SHA revisado: "+str(report["matches_independently_reviewed_sha"])+"\n"+
          "Contexto compatible: "+str(report["proposal_source_compatible"])+"\n"+
          "El generador no fue activado ni hizo llamadas API.\n"+
          "Toda propuesta futura exige revisión, regresiones y aprobación. No desplegar.\n")
        print(json.dumps({"compatible":report["proposal_source_compatible"],
                          "api_calls":0,"deployment_allowed":False}))
        return 0 if report["proposal_source_compatible"] else 2
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        print('patch_source_incompatible')
        return 2

if __name__=="__main__":
    raise SystemExit(main())