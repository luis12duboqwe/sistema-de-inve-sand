"""Safety, iteration, fail-closed and no-production tests for autonomous sales QA."""
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import json
import sales_autofix_loop as a
import build_sales_followup_candidate as builder

class AutoSalesLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=builder.BOT.read_text()
        cls.candidate=builder.make(cls.source)
    def test_reviewed_source_is_untouched(self):
        a.guard(self.source,self.candidate)
        self.assertEqual(a.sha(self.source),builder.FROZEN_SHA)
    def test_untrusted_source_change_rejected(self):
        with self.assertRaises(ValueError):
            a.guard(self.source+"tampered",self.candidate)
    def test_insertion_only(self):
        tampered=self.candidate.replace("PILOT_CONVERSATION_ID = 3",
                                       "PILOT_CONVERSATION_ID = 4")
        with self.assertRaises(ValueError):a.guard(self.source,tampered)
    def test_arbitrary_model_code_forbidden(self):
        modified=self.candidate.replace(
            "      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END",
            "      system('rm -rf /')\n      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END")
        with self.assertRaises(ValueError):a.guard(self.source,modified)
    def test_waha_repair_cross_scope_blocked(self):
        modified=self.candidate.replace(
            "      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END",
            "      WAHA\n      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END")
        with self.assertRaises(ValueError):a.guard(self.source,modified)
    def test_bounded_hardcoded_recipe(self):
        after=a.bounded_next(self.candidate,a.RECIPES[0])
        self.assertIn("reservas|reservame",after)
        self.assertNotEqual(after,self.candidate)
        self.assertTrue(a.guard(self.source,after))
    def test_recipe_anchor_drift_blocks(self):
        with self.assertRaises(ValueError):
            a.bounded_next(self.candidate,("not_exist","UNSEEN123","more"))
    def test_choose_recipe_from_failed_reservation(self):
        evidence={"generated_challenges":{"failed_ids":["rotation-02"]}}
        fixtures=[{"id":"rotation-02","family":"reservation"}]
        choice=a.choose_reviewed_recipe(evidence,fixtures,a.RECIPES)
        self.assertEqual(choice[0],"reserve_synonyms")
    def test_choose_recipe_from_shipping_only(self):
        evidence={"generated_challenges":{"failed_ids":["rotation-05"]}}
        fixtures=[{"id":"rotation-05","family":"shipping"}]
        choice=a.choose_reviewed_recipe(evidence,fixtures,a.RECIPES)
        self.assertEqual(choice[0],"shipping_eta_synonyms")
    def test_choose_recipe_does_not_accept_model_code(self):
        evidence={"generated_challenges":{"failed_ids":["rotation-05"]}}
        fixtures=[{"id":"rotation-05","family":"shipping"}]
        only=[r for r in a.RECIPES if r[0]=="negotiation_synonyms"]
        self.assertEqual(a.choose_reviewed_recipe(evidence,fixtures,only)[0],
                         "negotiation_synonyms")

    def test_no_client_actions_reported(self):
        r=a.initial()
        for k in ("candidate_deployed","candidate_integrated",
                  "deployment_authorized","real_inventory_modified",
                  "real_customer_data_loaded","active_ruby_modified"):
            self.assertFalse(r[k])
        self.assertEqual(r["public_messages_sent"],0)
        self.assertEqual(r["ai_api_calls"],0)
        self.assertTrue(r["manual_review_required"])
    def test_bounded_retries_stop_on_success(self):
        baseline={"candidate":False,"source_sha256":builder.FROZEN_SHA,
                  "scenarios":72,"passed":36,"public_messages_sent":0}
        incomplete={"dialogue_passed":70,"dialogue_total":72,
                    "holdout_passed":17,"holdout_total":18}
        complete={"dialogue_passed":72,"dialogue_total":72,
                  "holdout_passed":18,"holdout_total":18}
        with (patch.object(a.dialogue,"run",return_value=baseline),
              patch.object(a,"verified_generated_challenges",return_value=[]),
              patch.object(a.rotating,"tasks",return_value=[]),
              patch.object(a,"check_ruby",
                    side_effect=[(incomplete,False),(complete,True)]),
              patch.object(a,"legacy_regression",return_value=72),
              patch.object(a,"unit_regression",return_value=21),
              patch.object(a,"stage",return_value={
                "sha256":"a"*64,"auto_deploy":False})):
            r=a.one_cycle()
        self.assertEqual(len(r["evaluations"]),2)
        self.assertTrue(r["candidate_staged"])
        self.assertFalse(r["candidate_deployed"])
        self.assertEqual(r["status"],"qa_passed_review_required")
        self.assertEqual(r["evaluations"][1]["attempt"],2)
    def test_fails_closed_if_all_trials_fail(self):
        baseline={"candidate":False,"source_sha256":builder.FROZEN_SHA,
                  "scenarios":72,"passed":36,"public_messages_sent":0}
        with (patch.object(a.dialogue,"run",return_value=baseline),
              patch.object(a,"verified_generated_challenges",return_value=[]),
              patch.object(a.rotating,"tasks",return_value=[]),
              patch.object(a,"check_ruby",
                return_value=({"dialogue_passed":1,"holdout_passed":0},False))):
            r=a.one_cycle()
        self.assertEqual(len(r["evaluations"]),4)
        self.assertFalse(r["candidate_staged"])
        self.assertFalse(r["candidate_deployed"])
        self.assertEqual(r["status"],"no_more_safe_recipes")
    def test_drift_cannot_stage(self):
        with tempfile.TemporaryDirectory() as dirname:
            path=Path(dirname)/"sales-bot-v2.rb"
            path.write_text(self.source+"x")
            with (patch.object(a,"SOURCE",path),
                  patch.object(a,"stage",side_effect=AssertionError("staged"))):
                result=a.one_cycle()
        self.assertEqual(result["status"],"source_drift_blocked")
    def test_private_atomic_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/"private"/"case.txt"
            a.private_write(dest,"fictional")
            self.assertEqual(dest.read_text(),"fictional")
            self.assertEqual(dest.stat().st_mode & 0o077,0)

if __name__=="__main__":
    unittest.main()
