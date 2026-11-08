"""Repair workflow domain checks are fully synthetic, no real customers/staff."""
import unittest
from dataclasses import replace
from repair_workflow import (create,advance,run_synthetic_cases,
                             suggested_followup,TransitionDenied)

class RepairWorkflowTests(unittest.TestCase):
    def received(self):
        return create("SYN-00000001")
    def diagnosed(self):
        x=self.received()
        x=advance(x,"diagnosing","technician","event-a000",x.revision)
        return advance(x,"awaiting_approval","technician","event-b000",
                       x.revision,quote="1200.00")
    def approved(self):
        x=self.diagnosed()
        return advance(x,"approved","human_supervisor","event-c000",
                       x.revision,documented_human_approval=True)
    def repairing(self):
        x=self.approved()
        return advance(x,"repairing","technician","event-d000",
                       x.revision,parts_available=True)
    def test_sixty_cases(self):
        x=run_synthetic_cases(60)
        self.assertEqual(x["passed"],60)
        self.assertEqual(x["failed"],0)
        self.assertEqual(x["real_repairs"],0)
        self.assertEqual(x["public_messages_sent"],0)
    def test_bad_cases(self):
        for id in ("", "123456789","SYN-PHONE-999999999", "SYN-abcd", "SYN-ABC@"):
            with self.subTest(id=id):
                with self.assertRaises(TransitionDenied):create(id)
    def test_non_human_rejected(self):
        x=self.diagnosed()
        for actor in ("ai","bot","advisor",""):
            with self.subTest(actor=actor):
                with self.assertRaises(TransitionDenied):
                    advance(x,"approved",actor,"event-c000",x.revision,
                            documented_human_approval=True)
    def test_approval_guard(self):
        x=self.diagnosed()
        with self.assertRaises(TransitionDenied):
            advance(x,"approved","human_supervisor","event-c000",x.revision)
    def test_approval_only_after_quote(self):
        x=self.received()
        with self.assertRaises(TransitionDenied):
            advance(x,"approved","human_supervisor","event-z000",
                    x.revision,documented_human_approval=True)
    def test_cannot_repair_before_approval(self):
        x=self.diagnosed()
        with self.assertRaises(TransitionDenied):
            advance(x,"repairing","technician","event-d000",
                    x.revision,parts_available=True)
    def test_unavailable_parts_block_repair(self):
        x=self.approved()
        with self.assertRaises(TransitionDenied):
            advance(x,"repairing","technician","event-d000",
                    x.revision,parts_available=False)
        x=advance(x,"awaiting_parts","technician","event-e000",
                    x.revision,parts_available=False)
        self.assertEqual(x.stage,"awaiting_parts")
        x=advance(x,"repairing","technician","event-f000",
                    x.revision,parts_available=True)
        self.assertEqual(x.stage,"repairing")
    def test_qa_required_before_delivery(self):
        x=self.repairing()
        with self.assertRaises(TransitionDenied):
            advance(x,"ready","human_supervisor","event-g000",
                    x.revision,qa_passed=True)
        x=advance(x,"quality_check","technician","event-h000",x.revision)
        with self.assertRaises(TransitionDenied):
            advance(x,"ready","human_supervisor","event-i000",x.revision)
        x=advance(x,"ready","human_supervisor","event-i000",
                    x.revision,qa_passed=True)
        self.assertTrue(x.passed_quality_check)
        with self.assertRaises(TransitionDenied):
            advance(x,"delivered","technician","event-j000",x.revision)
        x=advance(x,"delivered","human_supervisor","event-j000",x.revision)
        self.assertEqual(x.stage,"delivered")
    def test_qa_fail_requires_repair_again(self):
        x=self.repairing()
        x=advance(x,"quality_check","technician","event-h000",x.revision)
        x=advance(x,"repairing","technician","event-k000",
                  x.revision,parts_available=True)
        self.assertFalse(x.passed_quality_check)
    def test_no_double_events(self):
        x=self.received()
        x=advance(x,"diagnosing","technician","event-a000",x.revision)
        y=advance(x,"diagnosing","technician","event-a000",0)
        self.assertIs(x,y)
        with self.assertRaises(TransitionDenied):
            advance(x,"cancelled","human_supervisor","event-a000",1)
    def test_stale_revision(self):
        x=self.received()
        with self.assertRaises(TransitionDenied):
            advance(x,"diagnosing","technician","event-a000",999)
    def test_quote_safety(self):
        x=self.received()
        x=advance(x,"diagnosing","technician","event-a000",x.revision)
        for amount in (None,0,-1,"nan","inf","-inf", "text", "100.999",
                       "1000001"):
            with self.subTest(amount=amount):
                with self.assertRaises(TransitionDenied):
                    advance(x,"awaiting_approval","technician",
                            "event-b000",x.revision,quote=amount)
    def test_cancel_only_human_before_work(self):
        x=self.diagnosed()
        with self.assertRaises(TransitionDenied):
            advance(x,"cancelled","technician","event-z000",x.revision)
        x=advance(x,"cancelled","human_supervisor","event-z000",x.revision)
        self.assertEqual(x.stage,"cancelled")
        with self.assertRaises(TransitionDenied):
            advance(x,"diagnosing","technician","event-y000",x.revision)
    def test_non_synthetic_cannot_process(self):
        x=replace(self.received(),synthetic_only=False)
        with self.assertRaises(TransitionDenied):
            advance(x,"diagnosing","technician","event-a000",x.revision)
    def test_handoff_no_real_actions(self):
        x=self.received()
        d=suggested_followup(x)
        self.assertFalse(d["contact_customer_automatically"])
        self.assertFalse(d["automated_payment"])
        self.assertFalse(d["inventory_mutations"])
    def test_invalid_test_limit(self):
        for n in (0,-1,501,True,"5"):
            with self.assertRaises(ValueError):run_synthetic_cases(n)

if __name__=="__main__":
    unittest.main()
