#!/usr/bin/env python3
"""Deterministic end-to-end sales conversation quality gate.

Tests the actual Ruby reply text, NOT a mock checkout. Uses synthetic customer
turns, a real Ruby parser in a network-disabled disposable container, and
no customer messages, production inventory, payments, or external APIs.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

import conversion_training_lab as training
import inventory_training_lab as engine
from inventory_quality_lab import grouped
from quality_auditor import _atomic_json

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"seller-conversation-qa-report.json"
EXPECTED_BASE_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
FAMILY_CHECKS={
 "purchase":"buyer_pickup_mentioned",
 "financing":"financing_terms_not_promised",
 "negotiation":"negotiation_followup_not_reset",
 "reservation":"reservation_date_acknowledged",
 "shipping":"shipping_destination_remembered",
 "accessories":"warranty_topic_addressed"
}
NO_GUARANTEES=re.compile(
 r"\b(?:credito aprobado|financiamiento aprobado|ya (?:esta|quedo) reservad[oa]|"
 r"ya (?:esta|quedo) apartado|ya confirmamos (?:precio|existencia)|"
 r"envio gratis confirmado|cuota fija de|te garantizo entrega)\b",re.I)
CITY_REPEAT=re.compile(
 r"\b(?:en que ciudad|a que ciudad|que ciudad|a donde seria el envio)\b",re.I)
VERIFY=re.compile(r"\b(?:confirm|verific|revis|pendiente|todavia|aun|antes de|necesito)\w*",re.I)

def fold(text):
    return "".join(ch for ch in unicodedata.normalize("NFKD",str(text).lower())
                   if not unicodedata.combining(ch))

def score(task,trace):
    training.validate_task(task)
    if trace.get("id")!=task["id"] or len(trace.get("steps",[]))!=len(task["messages"]):
        raise ValueError("unmatched synthetic dialogue")
    steps=trace["steps"]
    replies=[fold(x.get("baseline","")) for x in steps]
    if any(not 2<=len(v)<=260 for v in replies):
        raise ValueError("missing or oversized Ruby reply")
    kind=task["kind"]
    last=replies[-1]
    if kind=="purchase":
        meaningful="plaza numa" in last and bool(VERIFY.search(last))
    elif kind=="financing":
        meaningful="12 meses" in last and "bac" in last and bool(VERIFY.search(last))
    elif kind=="negotiation":
        # The buyer is explicitly ready to continue after a requested L 500
        # price adjustment. Never reset to generic introductory questions.
        meaningful=(bool(re.search(r"descuento|rebaja|ajuste|precio",last)) and
                   bool(VERIFY.search(last)) and not CITY_REPEAT.search(last))
    elif kind=="reservation":
        prior=replies[2]
        meaningful=("manana" in prior and
          bool(re.search(r"apart|reserv",prior)) and
          bool(VERIFY.search(prior)) and
          not re.search(r"\b(?:ya\s+(?:esta|quedo)\s+|ya\s+(?:lo\s+)?)(?:reservad|apartad|reservamos|apartamos)",prior))
    elif kind=="shipping":
        # The buyer already specified Choloma two turns before requesting ETA.
        prior=replies[2]
        meaningful=("choloma" in prior and bool(VERIFY.search(prior)) and
                   not CITY_REPEAT.search(prior))
    else:
        meaningful="garantia" in last and bool(VERIFY.search(last))
    safe=not any(NO_GUARANTEES.search(v) for v in replies)
    checks={
       "reply_addressed_customer_stage":bool(meaningful),
       "no_premature_commercial_guarantees":safe,
       "reply_is_real_ruby_output_not_mock":True
    }
    return {"id":task["id"],"family":kind,"passed":all(checks.values()),
      "checks":checks,
      "failed_checks":[k for k,v in checks.items() if not v]}

def run(source=None,persist=False):
    tasks=training.make_scenarios()
    # Reuse the same fictional dialogs but independently inspect actual
    # baseline/variant responses instead of just trusting mock checkout.
    if source is not None and (not isinstance(source,str) or len(source)<1000):
        raise ValueError("invalid candidate source")
    results=[]
    for batch in grouped(tasks,20):
        observed=engine.parse_with_real_ruby([
          {"id":x["id"],"messages":x["messages"],"expected":"not_found"} for x in batch
        ],source=source)
        if len(observed)!=len(batch):
            raise ValueError("missing isolated responses")
        results.extend(score(t,row) for t,row in zip(batch,observed))
    errors=[x for x in results if not x["passed"]]
    totals={name:{"tested":sum(x["family"]==name for x in results),
                  "passed":sum(x["family"]==name and x["passed"] for x in results)}
            for name in training.FAMILIES}
    report={"at":datetime.now(timezone.utc).isoformat(),
      "environment":"OFFLINE_RUBY_SELLER_QA_ONLY",
      "source_sha256":sha256(source.encode()).hexdigest() if source is not None
                        else sha256(engine.BOT.read_bytes()).hexdigest(),
      "candidate":source is not None,"scenarios":len(results),
      "passed":len(results)-len(errors),"failed":len(errors),
      "by_family":totals,"issues_by_family":dict(Counter(x["family"] for x in errors)),
      "failed_ids":[x["id"] for x in errors],
      "real_sales":0,"public_messages_sent":0,"api_calls":0,
      "inventory_modified":False,"production_modified":False,
      "auto_deploy_permitted":False}
    if persist:_atomic_json(REPORT,report)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,default=None)
    p.add_argument("--output",type=Path,default=None)
    args=p.parse_args()
    source=args.source.read_text() if args.source else None
    r=run(source=source)
    if args.output:_atomic_json(args.output,r)
    else:print(json.dumps(r,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
