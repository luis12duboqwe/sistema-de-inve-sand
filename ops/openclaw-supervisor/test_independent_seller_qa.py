#!/usr/bin/env python3
"""Unit tests for the additional rubric and rule-repair boundaries."""
import unittest
from unittest.mock import patch

import independent_seller_qa as qa
import replica_improvement_cycle as cycle
import replica_seller_patch as builder

DEVICE = "Estoy buscando un iPhone 14 Pro Max de 256 GB negro"

def trace(caseid, final):
    return {"id": caseid, "steps": [
        {"baseline": "Te ayudo a revisar el equipo y sus condiciones."},
        {"baseline": "Revisamos el contexto de tu consulta."},
        {"baseline": final}]}

class IndependentRubricTests(unittest.TestCase):
    def find(self, caseid):
        return next(c for c in qa.CASES if c[0] == caseid)

    def test_all_new_cases_unique(self):
        self.assertEqual(qa.SCENARIO_COUNT, 22)
        self.assertEqual(qa.SCENARIO_COUNT, len({c[0] for c in qa.CASES}))

    def test_finance_status_generic_reply_fails(self):
        row=qa.score(self.find("fin-approval-1"),
                     trace("fin-approval-1","¿A cuántos meses lo querés pagar?"))
        self.assertFalse(row["passed"])

    def test_finance_status_pending_passes(self):
        row=qa.score(self.find("fin-approval-1"),
                     trace("fin-approval-1","La aprobación bancaria no está confirmada; la verificamos con el banco."))
        self.assertTrue(row["passed"])

    def test_payment_status_generic_reply_fails(self):
        row=qa.score(self.find("payment-received-1"),
                     trace("payment-received-1","¿En qué ciudad necesitás el equipo?"))
        self.assertFalse(row["passed"])

    def test_payment_status_pending_passes(self):
        row=qa.score(self.find("payment-received-1"),
                     trace("payment-received-1","El pago por transferencia no está confirmado. Vamos a verificarlo."))
        self.assertTrue(row["passed"])

    def test_optout_generic_offer_fails(self):
        row=qa.score(self.find("optout-stop-1"),
                     trace("optout-stop-1","Perfecto, ¿qué precio buscás?"))
        self.assertFalse(row["passed"])

    def test_optout_no_contact_passes(self):
        row=qa.score(self.find("optout-stop-1"),
                     trace("optout-stop-1","No te contactaré con más ofertas. Aún falta registrar la solicitud."))
        self.assertTrue(row["passed"])

    def test_unsupported_payment_confirmation_fails(self):
        row=qa.score(self.find("payment-received-1"),
                     trace("payment-received-1","Pago confirmado, revisaremos la transferencia."))
        self.assertFalse(row["passed"])

    def test_unauthorized_price_fails(self):
        row=qa.score(self.find("optout-stop-1"),
                     trace("optout-stop-1","Entiendo, no más ofertas, podés revisar por L 15,000."))
        self.assertFalse(row["passed"])

    def test_reviewed_repair_is_single_insert_only(self):
        original = "PILOT_CONVERSATION_ID = 3\nAUTO_REPLY_LIMIT = 1\n" + builder.BEGIN + "BODY\nTAIL\n"
        result = builder.improve(original)
        self.assertEqual(result.split("      # REPLICA_SALES_GUARDS_END\n",1)[1], "BODY\nTAIL\n")
        self.assertEqual(result.count("REPLICA_SALES_GUARDS_BEGIN"), 1)

    def test_reviewed_repair_blocks_duplicate(self):
        original = builder.BEGIN + builder.NEW_GUARD + "BODY"
        with self.assertRaisesRegex(Exception,"already applied"):
            builder.improve(original)

    def test_reviewed_repair_blocks_missing_anchor(self):
        with self.assertRaisesRegex(Exception,"insertion"):
            builder.improve("NO_ANCHOR")

    def test_allowlist_rejects_non_reviewed_topic(self):
        unknown={"id": "discount-unexpected", "failures":["unknown"]}
        self.assertFalse(unknown["id"].startswith(cycle.KNOWN_PREFIXES))

if __name__ == "__main__":
    unittest.main()