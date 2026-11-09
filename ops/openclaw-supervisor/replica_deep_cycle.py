#!/usr/bin/env python3
"""Fail-closed recurring validation of the SHA-pinned deep Ruby sales candidate."""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json,sys
from pathlib import Path
import replica_cycle as core
import replica_deep_patch as gen
import replica_deep_heldout as held
import replica_qa_probe as regression
import independent_seller_qa as independent

LAB=Path("/opt/softmobile-waha-test/laboratorio-ia")
sys.path.insert(0,str(LAB))
from deep_sales_dialogue_lab import run as dialogue_run
from deep_sales_quality_gate import run as qualitative_run

ROOT=Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill")
REPORT=ROOT/"deep-lab-latest.json"
def parent_evidence():
    record=json.loads((ROOT/"independent-review.json").read_text())
    keys={"mode":"REPLICA_ADDITIONAL_INDEPENDENT_FIX_REVIEW",
          "status":"qa_passed_manual_review_required",
          "source_sha256":gen.LIVE_SHA,
          "candidate_sha256":gen.PARENT_SHA,
          "candidate_file":str(gen.PARENT),
          "public_release_permitted":False,
          "candidate_deployed":False,
          "production_modified":False,
          "external_independent_certification":False}
    for k,v in keys.items():
        if record.get(k)!=v or type(record.get(k))!=type(v):
            raise core.Blocked("incorrect upstream decision: "+k)
    if record.get("new_rubric_after",{}).get("passed")!=22 or record.get("new_rubric_after",{}).get("total")!=22:
        raise core.Blocked("upstream new QA not complete")
    fresh=datetime.fromisoformat(record["at"].replace("Z","+00:00"))
    age=(datetime.now(timezone.utc)-fresh).total_seconds()
    if not 0<=age<=9*3600:
        raise core.Blocked("upstream evidence expired")
    if gen.PARENT.is_symlink() or sha256(gen.PARENT.read_bytes()).hexdigest()!=gen.PARENT_SHA:
        raise core.Blocked("upstream Ruby differs from approved parent")
    if gen.LIVE.is_symlink() or sha256(gen.LIVE.read_bytes()).hexdigest()!=gen.LIVE_SHA:
        raise core.Blocked("active Ruby no longer matches frozen source")
    return record

def run():
    parent_evidence()
    build=gen.build()
    source_path=Path(build["candidate_file"])
    if source_path.is_symlink():
        raise core.Blocked("candidate symlink")
    source=source_path.read_text(encoding="utf-8")
    expected=build["candidate_sha256"]
    if sha256(source.encode()).hexdigest()!=expected:
        raise core.Blocked("staged candidate changed")
    deep=dialogue_run(source)
    quality=qualitative_run(deep)
    advanced=held.evaluate(source)
    base=regression.evaluate(source)
    extra=independent.evaluate(source)
    if (deep.get("turn_count")!=150 or deep.get("scenario_count")!=10 or
        deep.get("source_sha256")!=expected or deep.get("api_calls")!=0 or
        deep.get("public_messages_sent")!=0 or deep.get("stock_modified") is not False or
        deep.get("production_modified") is not False or
        quality.get("source_sha256")!=expected or quality.get("checks")!=32 or
        quality.get("passed")!=32 or quality.get("failed")!=0 or
        quality.get("independent_full_customer_qa_passed") is not True or
        advanced.get("source_sha256")!=expected or advanced.get("scenarios")!=13 or
        advanced.get("passed")!=13 or advanced.get("failed")!=[] or
        advanced.get("public_messages_sent")!=0 or
        base.get("source_sha256")!=expected or base.get("passed") is not True or
        extra.get("sha256")!=expected or extra.get("total")!=22 or
        extra.get("passed")!=22 or extra.get("public_messages_sent")!=0 or
        sha256(source_path.read_bytes()).hexdigest()!=expected or
        sha256(gen.LIVE.read_bytes()).hexdigest()!=gen.LIVE_SHA):
        raise core.Blocked("deep-seller regression or safety gate failed")
    return {
        "mode":"REPLICA_SALES_DEEP_REVIEW","status":"qa_passed_manual_review_required",
        "at":datetime.now(timezone.utc).isoformat(),"scope":"sales_only",
        "source_sha256":gen.LIVE_SHA,"parent_candidate_sha256":gen.PARENT_SHA,
        "candidate_sha256":expected,"candidate_file":str(source_path),
        "patch_file":build["patch_file"],
        "deep_dialogues":deep["scenario_count"],"deep_buyer_turns":deep["turn_count"],
        "deep_checks_passed":quality["passed"],"deep_checks_total":quality["checks"],
        "new_heldout_passed":advanced["passed"],"new_heldout_total":advanced["scenarios"],
        "commercial_72_passed":base["dialogue"]["passed"],
        "paraphrases_18_passed":base["heldout"]["passed"],
        "rotating_6_passed":base["rotating"]["passed"],
        "adversarial_11_passed":base["adversarial"]["passed"],
        "fictitious_checkout_72_passed":base["checkout"]["passed"],
        "additional_22_passed":extra["passed"],"unit_tests_passed":base["unit_tests_passed"],
        "synthetic_only":True,"independent_real_world_qa_passed":False,
        "commercial_data_verified":False,"public_release_permitted":False,
        "manual_review_required":True,"candidate_deployed":False,
        "production_modified":False,"public_messages_sent":0,"api_calls":0}

def persist(result):
    core.write_atomic(REPORT,core.to_json(result))
    if result["status"]=="qa_passed_manual_review_required":
        note=("# Replica Skill: QA profundo de ventas automatico\n\n"
             "Candidato APROBADO solo para revision manual; nunca para publico.\n\n"
             f"SHA candidato: {result['candidate_sha256']}\n\n"
             f"Dialogos largos: {result['deep_dialogues']}; "
             f"mensajes: {result['deep_buyer_turns']}; "
             f"criterios: {result['deep_checks_passed']}/{result['deep_checks_total']}.\n"
             f"Casos extra: {result['new_heldout_passed']}/{result['new_heldout_total']}.\n"
             f"Regresion: {result['commercial_72_passed']}/72; "
             f"reformulaciones {result['paraphrases_18_passed']}/18; "
             f"rotativos {result['rotating_6_passed']}/6; "
             f"adversariales {result['adversarial_11_passed']}/11.\n\n"
             "Sin produccion, WhatsApp, pagos ni inventario.\n"
             "No se certificaron precios reales, stock, proveedores ni ventas.\n")
    else:
        note="# Replica Skill: QA profundo de ventas\n\nBLOQUEADO.\n\nMotivo: "+str(result.get("reason"))+"\n"
    core.write_atomic(ROOT/"deep-lab-latest.md",note)

def main():
    try:
        result=run()
    except (core.Blocked,OSError,ValueError,KeyError,TypeError,IndexError,
            RuntimeError,TimeoutError) as exc:
        result={"mode":"REPLICA_SALES_DEEP_REVIEW","status":"blocked",
                "at":datetime.now(timezone.utc).isoformat(),
                "reason":str(exc)[:160],"candidate_deployed":False,
                "manual_review_required":True,"public_release_permitted":False,
                "production_modified":False,"public_messages_sent":0,"api_calls":0}
    persist(result)
    print(json.dumps({k:result.get(k) for k in
        ("status","candidate_sha256","deep_checks_passed","new_heldout_passed",
         "reason","public_release_permitted")},ensure_ascii=False))
    return 0 if result["status"]=="qa_passed_manual_review_required" else 2
if __name__=="__main__":
    raise SystemExit(main())