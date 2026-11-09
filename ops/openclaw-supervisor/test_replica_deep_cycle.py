"""Unit safety tests for the deep Ruby candidate review; no public actions."""
import json,tempfile,unittest
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import replica_cycle as core
import replica_deep_cycle as cycle
import replica_deep_patch as gen
import replica_deep_heldout as held

class DeepReviewGuards(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.live=root/"live.rb"
        self.parent=root/"parent.rb"
        self.parent.write_text("sample parent test source")
        self.live.write_text("sample active Ruby test source")
        self.report_dir=root/"reports"
        self.report_dir.mkdir()
        self.review={
            "mode":"REPLICA_ADDITIONAL_INDEPENDENT_FIX_REVIEW",
            "status":"qa_passed_manual_review_required",
            "source_sha256":sha256(self.live.read_bytes()).hexdigest(),
            "candidate_sha256":sha256(self.parent.read_bytes()).hexdigest(),
            "candidate_file":str(self.parent),
            "public_release_permitted":False,
            "candidate_deployed":False,
            "production_modified":False,
            "external_independent_certification":False,
            "new_rubric_after":{"passed":22,"total":22},
            "at":datetime.now(timezone.utc).isoformat()
        }
        self.patches=[
            patch.object(cycle,"ROOT",self.report_dir),
            patch.object(gen,"PARENT",self.parent),
            patch.object(gen,"LIVE",self.live),
            patch.object(gen,"PARENT_SHA",sha256(self.parent.read_bytes()).hexdigest()),
            patch.object(gen,"LIVE_SHA",sha256(self.live.read_bytes()).hexdigest())]
        for pt in self.patches:
            pt.start();self.addCleanup(pt.stop)
        self.flush()

    def flush(self):
        (self.report_dir/"independent-review.json").write_text(json.dumps(self.review))

    def test_parent_guard_valid(self):
        self.assertEqual(cycle.parent_evidence()["status"],"qa_passed_manual_review_required")

    def test_rejects_upstream_deployment(self):
        self.review["candidate_deployed"]=True;self.flush()
        with self.assertRaisesRegex(core.Blocked,"candidate_deployed"):
            cycle.parent_evidence()

    def test_rejects_stale_parent(self):
        self.review["at"]="2026-01-01T00:00:00Z";self.flush()
        with self.assertRaisesRegex(core.Blocked,"expired"):
            cycle.parent_evidence()

    def test_rejects_parent_hash_drift(self):
        self.parent.write_text(self.parent.read_text()+" # changed")
        with self.assertRaisesRegex(core.Blocked,"approved parent"):
            cycle.parent_evidence()

    def test_rejects_live_drift(self):
        self.live.write_text(self.live.read_text()+" # changed")
        with self.assertRaisesRegex(core.Blocked,"frozen source"):
            cycle.parent_evidence()

    def test_rejects_missing_independent_qa(self):
        self.review["new_rubric_after"]["passed"]=21;self.flush()
        with self.assertRaisesRegex(core.Blocked,"upstream new QA"):
            cycle.parent_evidence()

    def test_heldout_has_unique_and_bounded_fictional_cases(self):
        self.assertEqual(len(held.CASES),13)
        self.assertEqual(len({x[0] for x in held.CASES}),13)
        self.assertTrue(all(len(row[2])==3 for row in held.CASES))

if __name__=="__main__":
    unittest.main()