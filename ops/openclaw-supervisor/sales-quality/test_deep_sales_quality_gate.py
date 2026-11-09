"""Independent 10x15, 32-check deep-sales QA regression tests (fictional)."""
import copy,json,unittest
from pathlib import Path
import deep_sales_dialogue_lab as lab
import deep_sales_quality_gate as gate

ROOT=Path(__file__).resolve().parent/"quality"/"deep-sales-qa"
class DeepSalesQATests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=json.loads((ROOT/"current-10x15.json").read_text())
  cls.after=json.loads((ROOT/"candidate-10x15.json").read_text())
  cls.before_result=json.loads((ROOT/"current-evaluation.json").read_text())
  cls.after_result=json.loads((ROOT/"candidate-evaluation.json").read_text())
 def test_full_150_turns_each_not_partial_five(self):
  self.assertEqual(len(lab.CASES),10)
  self.assertTrue(all(len(c["messages"])==15 for c in lab.CASES))
  for report in (self.before,self.after):
   self.assertEqual(report["scenario_count"],10)
   self.assertEqual(report["turn_count"],150)
   self.assertEqual(sum(len(c["turns"]) for c in report["dialogues"]),150)
 def test_full_32_gate_has_no_automatic_approval(self):
  for transcript,evaluation in ((self.before,self.before_result),(self.after,self.after_result)):
   result=gate.run(transcript)
   self.assertEqual(result["checks"],32)
   self.assertEqual(result["passed"],evaluation["passed"])
   self.assertEqual(result["failed"],evaluation["failed"])
   self.assertFalse(result["independent_full_customer_qa_passed"])
   self.assertEqual(result["public_messages_sent"],0)
   self.assertFalse(result["code_deployed"])
 def test_candidate_improves_but_not_full_readiness(self):
  self.assertGreater(self.after_result["passed"],self.before_result["passed"])
  self.assertGreater(self.after_result["failed"],0)
  self.assertLess(self.after_result["passed"],32)
 def test_payment_and_optout_are_included(self):
  observed={i["check"] for i in self.after_result["failed_probes"]}
  for required in ("payment_status_not_auto_confirmed",
                   "short_model_reversion_recognized",
                   "after_cancel_no_more_reservation_sales"):
   self.assertIn(required,observed)
 def test_missing_trace_cannot_pass(self):
  damaged=copy.deepcopy(self.after)
  damaged["dialogues"][0]["turns"]=[]
  with self.assertRaises((IndexError,ValueError,StopIteration)):
   gate.run(damaged)
 def test_no_sensitive_records(self):
  for report in (self.before,self.after):
   self.assertEqual(report["public_messages_sent"],0)
   self.assertEqual(report["real_orders"],0)
   self.assertEqual(report["api_calls"],0)
   self.assertFalse(report["stock_modified"])
   self.assertFalse(report["production_modified"])
if __name__=="__main__":unittest.main()
