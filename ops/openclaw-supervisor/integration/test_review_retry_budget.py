"""Safety tests for bounded review retries and the versioned commercial contract."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lab_cycle as q
import review_loop as rev

UTC=dt.timezone.utc

class ReviewBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.daily=self.root/"daily.json"
        self.cooldown=self.root/"agent-budget.json"
        pt=patch.object(rev,"DAILY_AGENT_LEDGER",self.daily)
        pt.start()
        self.addCleanup(pt.stop)
        pt=patch.object(rev.q,"RESULTS",self.root)
        pt.start()
        self.addCleanup(pt.stop)
        self.now=dt.datetime(2026,11,9,14,5,tzinfo=UTC)

    def test_retry_limit_and_daily_cost_cap(self):
        self.assertEqual(rev.MAX_PASSES,3)
        self.assertEqual(rev.MAX_DAILY_AGENT_CALLS,6)
        for i in range(6):
            self.assertTrue(rev.reserve_model_call(self.now))
            self.assertEqual(rev.quota_available(self.now),5-i)
        self.assertFalse(rev.reserve_model_call(self.now))
        self.assertEqual(json.loads(self.daily.read_text())["calls"],6)

    def test_daily_budget_resets_on_new_utc_day(self):
        for i in range(6):
            self.assertTrue(rev.reserve_model_call(self.now))
        tomorrow=self.now+dt.timedelta(days=1)
        self.assertEqual(rev.quota_available(tomorrow),6)
        self.assertTrue(rev.reserve_model_call(tomorrow))
        d=json.loads(self.daily.read_text())
        self.assertEqual(d["day_utc"],tomorrow.date().isoformat())
        self.assertEqual(d["calls"],1)

    def test_corrupt_existing_quota_blocks_calls(self):
        self.daily.write_text("{malformed")
        self.assertEqual(rev.quota_available(self.now),0)
        self.assertFalse(rev.reserve_model_call(self.now))
        self.daily.write_text('{"day_utc":"2026-11-09","calls":true}')
        self.assertEqual(rev.quota_available(self.now),0)

    def test_cooldown_respected_after_contract_review(self):
        self.cooldown.write_text(json.dumps({
            "last_attempt_utc":dt.datetime.now(UTC).isoformat(),
            "policy_contract_sha":"policy-v2"}))
        allowed,delay,_,_=rev.should_call_agent({"commercial":{"passed":True,"tests":47}},"policy-v2")
        self.assertFalse(allowed)
        self.assertGreater(delay,0)

    def test_new_contract_allows_fresh_audit(self):
        self.cooldown.write_text(json.dumps({
            "last_attempt_utc":dt.datetime.now(UTC).isoformat(),
            "policy_contract_sha":"policy-v1"}))
        allowed,delay,_,_=rev.should_call_agent({"commercial":{"passed":True,"tests":47}},"policy-v2")
        self.assertTrue(allowed)
        self.assertEqual(delay,0)

    def test_review_credits_bound_to_contract(self):
        with tempfile.TemporaryDirectory() as d:
            stage=Path(d)
            root=stage/"laboratorio-ia"
            root.mkdir()
            (root/"test_a.py").write_text("assert True")
            (root/"implementation.py").write_text("choice=True")
            names=["laboratorio-ia/implementation.py","laboratorio-ia/test_a.py"]
            base=rev.audit_scope_fingerprint(stage,names)
            (root/"test_a.py").write_text("assert False")
            self.assertEqual(rev.audit_scope_fingerprint(stage,names),base)

    def test_policy_contract_is_explicit(self):
        self.assertIn("test_commercial_policy_contract",q.SUITES[3][2])
        contract=q.POLICY_CONTRACT.read_text()
        self.assertIn("SUPERSEDED =",contract)
        self.assertIn("self.assertNotIn(\"17,368\"",contract)
        self.assertNotIn("test_dialogos_aprobados","",json.dumps(q.SUITES))
        self.assertEqual(q.sha(q.SOURCE/"laboratorio-ia/test_dialogos_aprobados.py"),
                         q.LEGACY_COMMERCIAL_TEST_SHA)

if __name__=="__main__":
    unittest.main()