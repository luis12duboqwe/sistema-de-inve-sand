#!/usr/bin/env python3
"""Offline regression tests for the read-only supervisor."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import supervisor as s

class SupervisorTests(unittest.TestCase):
    def sample(self):
        return {"account_id":2,"inbox_id":2,"redacted":True,"coverage_complete":True,
                "public_messages_sent":0,"total_conversations":9,
                "reviewed_conversations":9,"queues":{"unanswered":[3,9],
                "recoverable":[7],"consented_followup":[],"human_review":[7]}}

    def test_actions_are_manual_only(self):
        acts=s.proposals(self.sample())
        self.assertEqual(len(acts),4)
        self.assertTrue(all(a["requires_approval"] for a in acts))
        self.assertTrue(all("conversation_id" in a for a in acts))

    def test_source_must_not_write_public_messages(self):
        self.assertIn("scope.find_each",s.RAILS)
        self.assertNotIn("Messages::MessageBuilder",s.RAILS)
        self.assertNotIn(".update!",s.RAILS)
        self.assertNotIn("create!",s.RAILS)
        self.assertIn("redacted:true,public_messages_sent:0",s.RAILS)

    def test_chatwoot_accepts_valid_scope(self):
        data=self.sample()
        class Output:
            returncode=0
            stdout=s.PREFIX+json.dumps(data)
        with patch.object(s,"shell",return_value=Output()):
            result=s.chatwoot()
        self.assertEqual(result["reviewed_conversations"],9)
        self.assertEqual(result["status"],"ok")

    def test_bad_account_is_blocked(self):
        d=self.sample();d["account_id"]=1
        class Output:
            returncode=0
            stdout=s.PREFIX+json.dumps(d)
        with patch.object(s,"shell",return_value=Output()):
            with self.assertRaises(ValueError):
                s.chatwoot()

    def test_incomplete_coverage_is_blocked(self):
        d=self.sample();d["coverage_complete"]=False
        class Output:
            returncode=0
            stdout=s.PREFIX+json.dumps(d)
        with patch.object(s,"shell",return_value=Output()):
            with self.assertRaises(ValueError):
                s.chatwoot()

    def test_chatwoot_failure_yields_alert_not_send(self):
        with patch.object(s,"chatwoot",side_effect=RuntimeError("offline")), \
             patch.object(s,"lab",return_value={"all_local_tests_passed":True}), \
             patch.object(s,"inventory",return_value={"orders_total":0,"orders_pending":0}), \
             patch.object(s,"photos",return_value={"older_than_2h_pending_review_ids":[]}), \
             patch.object(s,"health",return_value={"all_containers_running":True,
                    "whatsapp_online":True,"disk_free_percent":75,"memory_available_percent":50}):
            result=s.collect()
        self.assertEqual(result["chatwoot"]["status"],"unavailable")
        self.assertEqual(result["public_messages_sent"],0)
        self.assertEqual(result["proposed_actions"],[])
        self.assertGreaterEqual(len(result["alerts"]),1)

    def test_markdown_has_no_customer_message(self):
        d={"chatwoot":self.sample(),"quality":{"tests":492,
            "all_local_tests_passed":True},"health":{"all_containers_running":True,
            "disk_free_percent":75,"memory_available_percent":50},
            "alerts":[],"captured_utc":"2026-11-07T22:00:00Z",
            "proposed_actions":[]}
        report=s.markdown(d)
        self.assertIn("9/9",report)
        self.assertIn("SOLO LECTURA",report)
        self.assertNotIn("5555-1234",report)

    def test_inventory_sql_is_read_only(self):
        self.assertIn("BEGIN TRANSACTION READ ONLY;",s.INVENTORY_SQL)
        self.assertNotIn("UPDATE orders",s.INVENTORY_SQL)
        self.assertNotIn("DELETE FROM",s.INVENTORY_SQL)

    def test_inventory_snapshot_only_aggregates(self):
        values={"products_total":203,"active_products":203,
            "available_units":106,"reserved_units":0,
            "out_of_stock_active_products":135,"orders_total":458,
            "orders_pending":458,"orders_with_completed_at":0}
        class Output:
            returncode=0
            stdout="BEGIN\nSM_INV_JSON="+json.dumps(values)+"\nCOMMIT"
        with patch.object(s,"shell",return_value=Output()):
            got=s.inventory()
        self.assertTrue(got["read_only"])
        self.assertEqual(got["available_units"],106)
        self.assertNotIn("imei",got)
        self.assertNotIn("customer_phone",got)

    def test_stopped_whatsapp_causes_alert_without_restart(self):
        with patch.object(s,"chatwoot",return_value=self.sample()), \
             patch.object(s,"lab",return_value={"all_local_tests_passed":True}), \
             patch.object(s,"inventory",return_value={"orders_total":0,"orders_pending":0}), \
             patch.object(s,"photos",return_value={"older_than_2h_pending_review_ids":[]}), \
             patch.object(s,"health",return_value={"all_containers_running":True,
                     "whatsapp_online":False,"disk_free_percent":75,"memory_available_percent":50}):
            r=s.collect()
        self.assertIn("WAHA del entorno piloto", " ".join(r["alerts"]))
        self.assertEqual(r["public_messages_sent"],0)
        self.assertFalse(r["production_changed"])

    def test_release_gate_fails_closed_even_with_healthy_metrics(self):
        with patch.object(s,"chatwoot",return_value=self.sample()), \
             patch.object(s,"scan_followups",return_value=[]), \
             patch.object(s,"lab",return_value={"all_local_tests_passed":True,
                     "independent_convergence":True}), \
             patch.object(s,"inventory",return_value={"orders_total":0,"orders_pending":0}), \
             patch.object(s,"photos",return_value={"older_than_2h_pending_review_ids":[]}), \
             patch.object(s,"health",return_value={"all_containers_running":True,
                     "whatsapp_online":True,"disk_free_percent":75,"memory_available_percent":50}):
            result=s.collect()
        self.assertFalse(result["release_gates"]["public_messaging_ready"])
        self.assertFalse(result["release_gates"]["explicit_authorization_to_go_live"])
        self.assertEqual(result["followups"]["public_messages_sent"],0)

    def test_atomic_report_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"status.txt"
            with patch.object(s.os,"chown",return_value=None):
                s.save(p,"ok")
            self.assertEqual(p.read_text(),"ok")
            self.assertEqual(p.stat().st_mode & 0o777,0o640)

if __name__=="__main__":
    unittest.main(verbosity=2)
