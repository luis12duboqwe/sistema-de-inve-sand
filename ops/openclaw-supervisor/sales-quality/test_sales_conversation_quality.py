"""Sales-only shadow evaluator and candidate regression tests.

All model names, conversations, prices and stock states are fictional. The
current bot source is read but never edited. No production messages or APIs.
"""
from pathlib import Path
from hashlib import sha256
import re
import unittest

import build_sales_followup_candidate as builder
import sales_conversation_quality as quality
import conversion_training_lab as sales
import inventory_training_lab as ruby

def scenarios():
    return [
      {"id":"offer-test","messages":[
        "Busco iPhone 14 Pro Max 256 GB negro",
        "¿Me hacés descuento si pago en efectivo?",
        "¿Podés rebajarlo 500 lempiras?",
        "Si es posible sigo con la compra"],"expected":"not_found"},
      {"id":"reserve-test","messages":[
        "Busco iPhone 13 128 GB blanco",
        "¿Me lo pueden apartar?",
        "¿Puedo reservarlo para mañana?",
        "Quiero confirmar pero primero necesito saber si hay"],"expected":"not_found"},
      {"id":"ship-test","messages":[
        "Busco iPhone 14 Pro Max 256 GB negro",
        "¿Cuánto cuesta enviarlo a Choloma?",
        "¿En cuántos días llegaría?",
        "¿Cómo sería el pago?"],"expected":"not_found"},
      {"id":"pay-test","messages":[
        "Busco iPhone 15 128 GB azul",
        "Me interesa retirar en Plaza Numa",
        "Ya pagué por transferencia, ¿confirmás el pago?"],"expected":"not_found"},
      {"id":"shipping-tracking","messages":[
        "Busco iPhone 13 128 GB blanco",
        "Lo quiero con envío a Choloma",
        "¿Cuándo llegaría mi pedido? Ya pagué, tengo guía"],"expected":"not_found"},
      {"id":"cancel-test","messages":[
        "Busco Samsung S24 Ultra 256 GB azul",
        "¿Puedo reservarlo para mañana?",
        "Ya no me interesa, mejor cancelo la compra"],"expected":"not_found"}
    ]

class ShadowSalesQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=builder.BOT.read_text()
        cls.candidate=builder.make(cls.original)
        cls.records=ruby.parse_with_real_ruby(scenarios(),source=cls.candidate)
        cls.observed={r["id"]:r["steps"] for r in cls.records}
    def test_sha_anchor_guard(self):
        self.assertEqual(sha256(self.original.encode()).hexdigest(),builder.FROZEN_SHA)
        self.assertEqual(self.candidate.count("SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN"),1)
        self.assertEqual(self.original.count("SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN"),0)
    def test_drift_disallowed(self):
        with self.assertRaises(ValueError):
            builder.make(self.original+"\n# changed without review")
    def test_double_patch_disallowed(self):
        with self.assertRaises(ValueError):
            builder.make(self.candidate)
    def test_reply_is_real_ruby_not_mock(self):
        result=quality.score(sales.make_scenarios()[2],
                            {"id":"sale-00-negotiation",
                             "steps":[{"baseline":"Un asesor revisará esa información."}
                                      for _ in range(4)]})
        self.assertFalse(result["passed"])
    def test_known_city_retained_in_shipping_cost(self):
        reply=quality.fold(self.observed["ship-test"][1]["baseline"])
        self.assertIn("choloma",reply)
        self.assertIn("costo",reply)
        self.assertNotRegex(reply,quality.CITY_REPEAT)
        self.assertNotRegex(reply,r"l\s*\d{3,7}\b")
    def test_known_city_retained_in_shipping_eta(self):
        reply=quality.fold(self.observed["ship-test"][2]["baseline"])
        self.assertIn("choloma",reply)
        self.assertIn("plazo",reply)
        self.assertNotRegex(reply,quality.CITY_REPEAT)
        self.assertNotIn("en 3 dias",reply)
    def test_negotiation_does_not_reset_buyer(self):
        reply=quality.fold(self.observed["offer-test"][-1]["baseline"])
        self.assertIn("precio",reply)
        self.assertIn("condicion",reply)
        self.assertIn("verific",reply) if "verific" in reply else self.assertIn("confirm",reply)
        self.assertNotRegex(reply,quality.CITY_REPEAT)
        self.assertNotRegex(reply,r"\brebaja (?:aprobada|confirmada)\b")
    def test_reservation_request_not_confirmed(self):
        reply=quality.fold(self.observed["reserve-test"][2]["baseline"])
        self.assertIn("manana",reply)
        self.assertIn("no esta reservado",reply)
        self.assertNotRegex(reply,r"ya (?:lo )?reservamos|ya esta reservado")
    def test_payment_confirmation_not_fabricated(self):
        reply=quality.fold(self.observed["pay-test"][-1]["baseline"])
        self.assertNotRegex(reply,r"pago (?:confirmado|recibido)|ya recibimos")
        self.assertNotRegex(reply,r"\b(?:l|hnl)\s*\d{4,7}\b")
    def test_existing_order_eta_cannot_claim_delivery(self):
        reply=quality.fold(self.observed["shipping-tracking"][-1]["baseline"])
        self.assertNotRegex(reply,r"\b(?:llega manana|llega en \d+ dias|ya se entrego)\b")
        self.assertNotRegex(reply,r"\bpago confirmado\b")
    def test_cancel_does_not_automatically_create_sale(self):
        reply=quality.fold(self.observed["cancel-test"][-1]["baseline"])
        self.assertNotRegex(reply,r"\b(?:ya te lo apartamos|ya esta reservado|compra confirmada)\b")
    def test_no_customer_data_or_external_links_in_candidate(self):
        patch=builder.ADDITIONS
        self.assertNotIn("http://",patch)
        self.assertNotIn("https://",patch)
        self.assertNotIn("system(",patch)
        self.assertNotIn("Chatwoot",patch)
        self.assertNotIn("WAHA",patch)
        self.assertNotIn("API_KEY",patch)
    def test_quality_rejects_premature_promise(self):
        case=next(x for x in sales.make_scenarios() if x["kind"]=="reservation")
        truth=case["truth"]
        fake={"id":case["id"],"steps":[{"baseline":"Reserva en revisión",
                 "model":truth["model"],"capacity":f"{truth['capacity_gb']}GB",
                 "color":truth["color"]} for _ in range(4)]}
        fake["steps"][2]["baseline"]="Ya está reservado para mañana, sin problema."
        res=quality.score(case,fake)
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["no_premature_commercial_guarantees"])

if __name__=="__main__":
    unittest.main()
