"""Synthetic-only repair lab and integration source tests."""
import unittest
from repair_lab_runner import analyze,markdown

def probe():
    return {"repair_cases_table_exists":False,
            "repair_events_table_exists":False,
            "backend_repair_router_file_exists":False,
            "backend_repair_model_file_exists":False,
            "real_workflow_verified":False}

class RepairLabRunnerTests(unittest.TestCase):
    def test_unconnected_evidence_is_explicit(self):
        out=analyze("2026-11-08T00:00:00+00:00",probe())
        self.assertFalse(out["repair_workflow_connected"])
        self.assertEqual(out["offline_domain_cases"],60)
        self.assertEqual(out["offline_domain_passed"],60)
        self.assertEqual(out["real_repair_cases_processed"],0)
        self.assertFalse(out["production_changed"])
    def test_even_source_tables_do_not_establish_workflow(self):
        data={k:True for k in probe()}
        report=analyze("2026-11-08T00:00:00+00:00",data)
        self.assertFalse(report["repair_workflow_connected"])
    def test_source_invalid_types_rejected(self):
        item=probe()
        item["repair_cases_table_exists"]="false"
        with self.assertRaises(ValueError):
            analyze("2026-11-08T00:00:00+00:00",item)
    def test_case_count_less_rejected(self):
        fake={"environment":"SYNTHETIC_OFFLINE_ONLY",
              "cases":60,"passed":59,"failed":1,"real_repairs":0,
              "public_messages_sent":0,"payments_initiated":0,
              "real_inventory_mutations":0,"source_connected":False}
        with self.assertRaises(ValueError):
            analyze("2026-11-08T00:00:00+00:00",probe(),fake)
    def test_public_message_rejected(self):
        fake={"environment":"SYNTHETIC_OFFLINE_ONLY","cases":60,
              "passed":60,"failed":0,"real_repairs":0,
              "public_messages_sent":1,"payments_initiated":0,
              "real_inventory_mutations":0,"source_connected":False}
        with self.assertRaises(ValueError):
            analyze("2026-11-08T00:00:00+00:00",probe(),fake)
    def test_report_honestly_labels_offline(self):
        md=markdown(analyze("2026-11-08T00:00:00+00:00",probe()))
        self.assertIn("PENDIENTE",md)
        self.assertIn("Casos reales tratados: 0",md)

if __name__=="__main__":
    unittest.main()
