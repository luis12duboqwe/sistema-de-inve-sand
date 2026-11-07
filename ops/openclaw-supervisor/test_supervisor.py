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

    def test_atomic_report_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"status.txt"
            with patch.object(s.os,"chown",return_value=None):
                s.save(p,"ok")
            self.assertEqual(p.read_text(),"ok")
            self.assertEqual(p.stat().st_mode & 0o777,0o640)

if __name__=="__main__":
    unittest.main(verbosity=2)
