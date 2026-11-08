"""Pinned current Ruby patch staging, no AI calls or code execution."""
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

import patch_source_compat as p

class PatchCompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=p.BOT.read_text()
        cls.sha=hashlib.sha256(cls.source.encode()).hexdigest()
    def test_pinned_source_compatible(self):
        self.assertEqual(self.sha,p.KNOWN_SHA)
        self.assertTrue(p.compatible(self.source))
    def test_any_change_needs_review(self):
        self.assertFalse(p.compatible(self.source+"\n# unreviewed\n"))
    def test_invalid_source(self):
        self.assertFalse(p.compatible(123))
        self.assertFalse(p.compatible(""))
    def test_wrong_sha_rejected(self):
        self.assertFalse(p.compatible(self.source,"0"*64))
    def test_missing_scope_rejected_when_re_pinned(self):
        changed=self.source.replace("PILOT_CONVERSATION_ID = 3","PILOT_CONVERSATION_ID = 5")
        sha=hashlib.sha256(changed.encode()).hexdigest()
        self.assertFalse(p.compatible(changed,sha))
    def test_unique_anchor_required(self):
        doubled=self.source+p.SAFETY_ANCHOR
        sha=hashlib.sha256(doubled.encode()).hexdigest()
        self.assertFalse(p.compatible(doubled,sha))
    def test_report_stays_inert(self):
        r=p.evidence(self.source,"2026-11-08T00:00:00+00:00")
        self.assertTrue(r["proposal_source_compatible"])
        self.assertFalse(r["patch_timer_approved"])
        self.assertFalse(r["deployment_allowed"])
        self.assertEqual(r["api_calls_made"],0)
        self.assertEqual(r["proposals_staged"],0)

if __name__=="__main__":
    unittest.main()
