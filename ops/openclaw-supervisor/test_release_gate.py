"""Fail-closed release certification tests. No network or external writes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import release_gate as r
from test_event_router import fixtures,prepare

def inputs():
    sup,d,op=fixtures()
    sup["chatwoot"].update({"account_id":2,"inbox_id":2})
    sup["quality"]={"all_local_tests_passed":True,"independent_convergence":False}
    sup["health"]={"whatsapp_online":False}
    sup["release_gates"]={
        "public_messaging_ready":False,"pilot_transport_online":False,
        "independent_qa_converged":False,"commercial_actions_enabled":False}
    d["synthetic_sales"]={"available":True,"scenarios":72,"passed":72,"failed":0,
                          "synthetic_only":True,"public_messages_sent":0}
    d["verified_finance"]={"completed_orders":0,"daily_closes":0,"profit_verified":False}
    ev={"schema_version":1,"mode":"internal_event_queue",
        "source_utc":d["source_utc"],"queued":1,
        "work_queue":[{"task_id":"ventas_respuestas","state":"awaiting_human"}],
        "external_commercial_actions":0,"public_messages_sent":0}
    return sup,d,op,ev

class ReleaseTests(unittest.TestCase):
    def test_blocked_when_test_pass(self):
        obj=r.report(*inputs())
        self.assertFalse(obj["public_release_permitted"])
        self.assertTrue(obj["checks"]["fictional_sales_qa_passed"])
        self.assertIn("real_whatsapp_chatwoot_full_cycle_verified",
                      obj["blocked_sales_launch"])
        self.assertIn("explicit_owner_launch_approval",
                      obj["blocked_sales_launch"])
        self.assertEqual(obj["public_messages_sent"],0)
        self.assertTrue(obj["qa_simulation_not_real_sale"])
    def test_all_machine_flags_cannot_go_live(self):
        sup,d,op,ev=inputs()
        sup["release_gates"].update(
            {"pilot_transport_online":True,"independent_qa_converged":True,
             "commercial_actions_enabled":True})
        sup["health"]["whatsapp_online"]=True
        sup["quality"]["independent_convergence"]=True
        d["verified_finance"]={"completed_orders":100,"daily_closes":1,
                               "profit_verified":True}
        obj=r.report(sup,d,op,ev)
        self.assertFalse(obj["public_release_permitted"])
        self.assertFalse(obj["checks"]["explicit_owner_launch_approval"])
        self.assertFalse(obj["checks"]["real_whatsapp_chatwoot_full_cycle_verified"])
    def test_no_finance_from_pending_orders(self):
        obj=r.report(*inputs())
        self.assertFalse(obj["checks"]["real_orders_reconciled"])
    def test_no_repairs_ads_assumptions(self):
        obj=r.report(*inputs())
        self.assertFalse(obj["checks"]["repair_workflow_connected"])
        self.assertFalse(obj["checks"]["meta_ads_data_connected"])
    def test_wrong_account_not_covered(self):
        sup,d,op,ev=inputs()
        sup["chatwoot"]["account_id"]=999
        self.assertFalse(r.report(sup,d,op,ev)["checks"]["chatwoot_pilot_coverage_verified"])
    def test_wrong_simulation_count(self):
        sup,d,op,ev=inputs()
        d["synthetic_sales"]["scenarios"]=71
        self.assertFalse(r.report(sup,d,op,ev)["checks"]["fictional_sales_qa_passed"])
    def test_wrong_source_mismatch(self):
        sup,d,op,ev=inputs()
        ev["source_utc"]="2026-01-01T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prepare(root,sup,d,op)
            (root/"EVENTS.json").write_text(json.dumps(ev))
            with self.assertRaises(r.Reject):r.validated_inputs(root)
    def test_external_writes_rejected(self):
        sup,d,op,ev=inputs()
        op["external_actions"]=1
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prepare(root,sup,d,op)
            (root/"EVENTS.json").write_text(json.dumps(ev))
            with self.assertRaises(r.Reject):r.validated_inputs(root)
    def test_real_healthy_context_valid(self):
        sup,d,op,ev=inputs()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prepare(root,sup,d,op)
            (root/"EVENTS.json").write_text(json.dumps(ev))
            s,di,o,e=r.validated_inputs(root)
            self.assertEqual(di["source_utc"],e["source_utc"])
    def test_certification_markdown(self):
        obj=r.report(*inputs())
        md=r.markdown(obj)
        self.assertIn("BLOQUEADO",md)
        self.assertNotIn("ACTIVAR AUTOMÁTICAMENTE",md)
        self.assertIn("Lanzamiento",md)
    def test_offline_workstreams_require_source_match(self):
        sup,d,op,ev=inputs()
        sup["inventory"]={"status":"ok","read_only":True}
        finance={"source_utc":d["source_utc"],"mode":"finance_read_only_audit",
                 "read_only":True,"customer_data_extracted":False,
                 "payments_initiated":0,"profit_verified":False,"revenue_verified":False}
        repair={"source_utc":d["source_utc"],
                "mode":"repair_simulation_and_source_probe",
                "offline_domain_cases":60,"offline_domain_passed":60,
                "real_repair_cases_processed":0,"public_messages_sent":0,
                "repair_workflow_connected":False}
        out=r.report(sup,d,op,ev,finance=finance,repairs=repair)
        self.assertTrue(out["non_whatsapp_readiness"]["finance_audit_available"])
        self.assertTrue(out["non_whatsapp_readiness"]["repair_domain_synthetic_qa_passed"])
        self.assertFalse(out["non_whatsapp_readiness"]["real_repair_workflow_connected"])
        self.assertFalse(out["public_release_permitted"])
        finance["source_utc"]="stale"
        out=r.report(sup,d,op,ev,finance=finance,repairs=repair)
        self.assertFalse(out["non_whatsapp_readiness"]["finance_audit_available"])
    def test_no_inferred_ads_or_code_approval(self):
        obj=r.report(*inputs())
        self.assertFalse(obj["non_whatsapp_readiness"]["advertising_data_source_connected"])
        self.assertFalse(obj["non_whatsapp_readiness"]["autonomous_code_review_source_gate"])
        self.assertTrue(obj["whatsapp_deferred_until_final_phase"])
    def test_sales_certificate_excludes_paused_repairs(self):
        sup,d,op,ev=inputs()
        d["scope"]="sales_only"
        obj=r.sales_scope_report(r.report(sup,d,op,ev),d)
        self.assertEqual(obj["scope"],"sales_only")
        self.assertNotIn("repair_workflow_connected",obj["checks"])
        self.assertNotIn("real_repair_workflow_connected",obj["non_whatsapp_readiness"])
        self.assertNotIn("repair_domain_synthetic_qa_passed",obj["non_whatsapp_readiness"])
        self.assertNotIn("repair_workflow_connected",obj["blocked_full_autonomy"])
        self.assertEqual(obj["non_whatsapp_total"],11)
        self.assertFalse(obj["non_whatsapp_readiness"]["reference_only_ai_commercial_firewall_passed"])
        self.assertFalse(obj["non_whatsapp_readiness"]["autonomous_sales_review_candidate_staged"])
        self.assertFalse(obj["non_whatsapp_readiness"]["ruby_sales_conversation_quality_passed"])
        self.assertEqual(obj["public_messages_sent"],0)
        self.assertFalse(obj["public_release_permitted"])
    def test_sales_certificate_rejects_missing_focus(self):
        sup,d,op,ev=inputs()
        with self.assertRaises(r.Reject):
            r.sales_scope_report(r.report(sup,d,op,ev),d)

    def test_always_boolean_false_public_release(self):
        obj=r.report(*inputs())
        self.assertIs(obj["public_release_permitted"],False)

if __name__=="__main__":
    unittest.main()
