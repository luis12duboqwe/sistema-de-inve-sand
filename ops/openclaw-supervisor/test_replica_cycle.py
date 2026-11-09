#!/usr/bin/env python3
"""No-network fault injection for Replica's production safety gates."""
import difflib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import replica_cycle as app

def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()

class ReplicaSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.base = root / "production"
        self.lab = self.base / "laboratorio-ia"
        self.quality = self.lab / "quality/autonomous-sales"
        self.candidates = self.quality / "candidates"
        self.candidates.mkdir(parents=True)
        self.source = self.base / "sales-bot-v2.rb"
        self.original = "    # safe baseline\n      # SM_AUTO_POLICY_HOOK_END\n    done\n"
        self.candidate_text = "    # safe baseline\n      # SM_AUTO_POLICY_HOOK_END\n      # SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN\n      x = 'safe'\n      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END\n    done\n"
        self.source.write_text(self.original)
        self.sha = digest(self.candidate_text)
        self.candidate = self.candidates / f"candidate-{self.sha[:16]}.rb"
        self.candidate.write_text(self.candidate_text)
        self.diff = self.candidates / f"candidate-{self.sha[:16]}.patch"
        self.diff.write_text("".join(difflib.unified_diff(
            self.original.splitlines(True), self.candidate_text.splitlines(True),
            fromfile="a/sales-bot-v2.rb", tofile="b/sales-bot-v2.rb")))
        self.input = self.quality / "latest.json"
        self.cert = root / "CERTIFICATION.json"
        self.cert.write_text(json.dumps({"public_release_permitted": False, "scope": "sales_only"}))
        self.report = {
            "environment": "OFFLINE_AUTONOMOUS_SALES", "scope": "sales_only",
            "status": "qa_passed_review_required", "source_pinned": True,
            "candidate_staged": True, "candidate_integrated": False,
            "candidate_deployed": False, "deployment_authorized": False,
            "manual_review_required": True, "public_messages_sent": 0,
            "real_sales": 0, "payments_initiated": 0,
            "real_inventory_modified": False, "real_customer_data_loaded": False,
            "active_ruby_modified": False, "source_sha256": digest(self.original),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "winning_candidate": {
                "sha256": self.sha, "candidate_file": str(self.candidate),
                "patch_file": str(self.diff), "auto_deploy": False},
            "evaluations": [{"status": "qa_passed_review_required"}]}
        self.patches = [
            patch.object(app, "INPUT", self.input),
            patch.object(app, "SOURCE", self.source),
            patch.object(app, "EXPECTED_SOURCE_SHA", digest(self.original)),
            patch.object(app, "CERT", self.cert),
            patch.object(app, "ALLOWED_DIR", self.candidates)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.flush()

    def flush(self):
        self.input.write_text(json.dumps(self.report))

    def test_valid_source_and_patch(self):
        data, original, candidate = app.preflight()
        self.assertEqual(candidate, self.candidate)
        self.assertEqual(original, self.original.encode())
        self.assertIs(data["candidate_deployed"], False)

    def test_rejects_candidate_tampering(self):
        self.candidate.write_text(self.candidate_text + "# tampered\n")
        with self.assertRaisesRegex(app.Blocked, "hash mismatch"):
            app.preflight()

    def test_rejects_public_authorization_changed(self):
        self.cert.write_text(json.dumps({"public_release_permitted": True, "scope": "sales_only"}))
        with self.assertRaisesRegex(app.Blocked, "certification"):
            app.preflight()

    def test_rejects_source_drift(self):
        self.source.write_text(self.original + "# drift\n")
        with self.assertRaisesRegex(app.Blocked, "source drift"):
            app.preflight()

    def test_rejects_mismatched_diff(self):
        self.diff.write_text("made-up patch")
        with self.assertRaisesRegex(app.Blocked, "patch does not reproduce"):
            app.preflight()

    def test_rejects_candidate_symlink(self):
        temp = self.candidates / "other.rb"
        temp.write_text(self.candidate_text)
        self.candidate.unlink()
        self.candidate.symlink_to(temp)
        with self.assertRaisesRegex(app.Blocked, "linked"):
            app.preflight()

    def test_rejects_deployment_flag(self):
        self.report["candidate_deployed"] = True
        self.flush()
        with self.assertRaisesRegex(app.Blocked, "candidate_deployed"):
            app.preflight()

    def test_rejects_stale_report(self):
        self.report["completed_at"] = "2025-01-01T00:00:00Z"
        self.flush()
        with self.assertRaisesRegex(app.Blocked, "stale"):
            app.preflight()

    def test_rejects_wrong_patch_directory(self):
        outside = self.base / self.diff.name
        outside.write_text(self.diff.read_text())
        self.report["winning_candidate"]["patch_file"] = str(outside)
        self.flush()
        with self.assertRaisesRegex(app.Blocked, "patch metadata"):
            app.preflight()

if __name__ == "__main__":
    unittest.main()