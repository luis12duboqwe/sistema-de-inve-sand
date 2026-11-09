#!/usr/bin/env python3
"""Offline QA of a pinned candidate. No network, production writes or external API."""
import argparse
from hashlib import sha256
import json
import sys
from pathlib import Path

LAB = Path("/opt/softmobile-waha-test/laboratorio-ia")
sys.path.insert(0, str(LAB))
import sales_conversation_quality as conversations
import sales_heldout_challenges as heldout
import sales_adversarial_quality as adversarial
import sales_rotating_challenges as rotating
import sales_autofix_loop as autofix

def evaluate(source):
    digest = sha256(source.encode()).hexdigest()
    dialogue = conversations.run(source=source, persist=False)
    unseen = heldout.run(source=source)
    edges = adversarial.run(source=source)
    rotating_tasks = rotating.tasks()
    challenge, challenge_ok = autofix.check_generated(source, rotating_tasks)
    checkout = autofix.legacy_regression(source)
    units = autofix.unit_regression()
    if not (dialogue["source_sha256"] == digest
            and unseen["source_sha256"] == digest
            and edges["source_sha256"] == digest):
        raise ValueError("qa_source_sha_mismatch")
    if any(x.get("public_messages_sent") != 0 for x in (dialogue, unseen, edges)):
        raise ValueError("qa_external_action_detected")
    data = {
        "mode": "REPLICA_OFFLINE_QA",
        "source_sha256": digest,
        "synthetic_only": True,
        "network_allowed": False,
        "real_customer_data_loaded": False,
        "public_messages_sent": 0,
        "production_modified": False,
        "deployment_allowed": False,
        "dialogue": {"passed": dialogue["passed"], "total": dialogue["scenarios"],
                     "by_family": dialogue["by_family"]},
        "heldout": {"passed": unseen["passed"], "total": unseen["scenarios"]},
        "adversarial": {"passed": edges["passed"], "total": edges["scenarios"]},
        "rotating": {"passed": challenge["passed"], "total": challenge["tested"]},
        "checkout": {"passed": checkout, "total": 72},
        "unit_tests_passed": units,
    }
    data["passed"] = bool(
        dialogue["scenarios"] == 72 and dialogue["passed"] == 72
        and unseen["scenarios"] == 18 and unseen["passed"] == 18
        and edges["scenarios"] == 11 and edges["passed"] == 11
        and len(rotating_tasks) == 6 and challenge_ok and challenge["tested"] == 6
        and checkout == 72 and units >= 68)
    return data

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", type=Path, required=True)
    a = p.parse_args()
    if a.candidate.is_symlink():
        raise ValueError("symlink candidate")
    source = a.candidate.read_text(encoding="utf-8")
    if not 1000 < len(source) < 250000:
        raise ValueError("source_size_invalid")
    result = evaluate(source)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())