#!/usr/bin/env python3
"""Bounded AI proposal runner: maintain four-call cap even if development is unlimited.

Only stages inert review files via the existing patch_proposer.py; no merges,
Chatwoot writes, public messages, production deployments or stock updates.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

LAB=Path("/opt/softmobile-waha-test/laboratorio-ia")
MAX_DAILY=4

def cap(value):
    if type(value) is not int or value < 1:
        raise ValueError("invalid proposal request budget")
    return min(value,MAX_DAILY)

def main():
    sys.path.insert(0,str(LAB))
    import groq_usage_policy
    groq_usage_policy.request_cap=cap
    # Imported after the override, including transitive synthetic lab modules.
    import patch_proposer
    if patch_proposer.MAX_DAILY != MAX_DAILY:
        raise RuntimeError("proposal API cap was bypassed")
    if os.environ.get("SOFTMOBILE_UNTRUSTED_PROPOSALS_ENABLED")!="true":
        raise RuntimeError("proposals disabled")
    sys.argv=["patch_proposer.py","--run"]
    return patch_proposer.main()

if __name__=="__main__":
    raise SystemExit(main())
