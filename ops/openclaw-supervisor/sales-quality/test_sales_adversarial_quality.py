"""Regression for independent colloquial commerce edge cases."""
import unittest
from pathlib import Path
import build_sales_followup_candidate as builder
import sales_adversarial_quality as edge
import sales_autofix_loop as loop

class EdgeCaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=builder.BOT.read_text()
  cls.candidate=builder.make(cls.source)
  cls.baseline=edge.run()
  cls.reviewed=edge.run(source=cls.candidate)
 def test_baseline_catches_previous_errors(self):
  self.assertEqual(self.baseline["scenarios"],11)
  self.assertLess(self.baseline["passed"],11)
  self.assertIn("edges-07",self.baseline["failed_ids"])
 def test_candidate_passes_all(self):
  self.assertEqual(self.reviewed["passed"],11)
  self.assertEqual(self.reviewed["failed_ids"],[])
 def test_no_external_actions(self):
  for result in (self.baseline,self.reviewed):
   self.assertEqual(result["api_calls"],0)
   self.assertEqual(result["public_messages_sent"],0)
   self.assertEqual(result["real_sales"],0)
   self.assertFalse(result["production_changed"])
 def test_reviewed_recipe_source_pin(self):
  self.assertTrue(loop.guard(self.source,self.candidate))
 def test_cancel_vs_reserve_context(self):
  self.assertTrue(self.reviewed["by_topic"]["cancel_interest"])
  self.assertTrue(self.reviewed["by_topic"]["reserve_friday"])
  self.assertTrue(self.reviewed["by_topic"]["reserve_wednesday"])
 def test_payment_and_finance_distinct(self):
  self.assertTrue(self.reviewed["by_topic"]["finance_not_approved"])
  self.assertTrue(self.reviewed["by_topic"]["payment_unverified"])
 def test_shipping_cost_not_product_price(self):
  self.assertTrue(self.reviewed["by_topic"]["shipment_price"])
  self.assertTrue(self.reviewed["by_topic"]["shipment_days"])
 def test_failed_edge_selected_for_reviewed_recipe(self):
  r={"adversarial_cases":{"failed_ids":["edges-02"]}}
  selected=loop.choose_reviewed_recipe(r,[],loop.RECIPES)
  self.assertEqual(selected[0],"reserve_synonyms")
 def test_bad_qa_trace_rejected(self):
  case=edge.records()[0]
  with self.assertRaises(ValueError):
   edge.score(case,{"id":"bad","steps":[]})

if __name__=="__main__":unittest.main()
