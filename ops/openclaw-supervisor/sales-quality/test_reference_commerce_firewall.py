"""Commercial fact firewall for the non-live reference-only sales AI lab.

These tests explicitly trigger the real approved-commerce override, not only
the JSON model response. No API calls, PII, stock edits, or messaging.
"""
import re
import unittest
from approved_commerce import approved_reply
from sales_ai_agent import (
    Conversation,respond,reference_commerce_safe,safe_reference_sales_reply,
    AgentBlocked,grounded_reply)
from reference_inventory import ReferenceCatalog

MODEL="iPhone 14 Pro Max"
class ReferenceCommerceFirewallTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.reference=ReferenceCatalog()
 def provider(self,stage,ctx):
  if stage=="extract":
   return {"intent":"price","model":MODEL,"storage_gb":256,
           "color":"Negro","human_review":True}
  return {"reply":"Necesito verificar precio actual y existencia antes de cotizarte."}
 def test_old_catalog_price_is_really_in_old_script(self):
  raw=approved_reply("Cuánto vale iPhone 14 Pro Max 256 GB negro",[])
  self.assertRegex(raw,r"L\s*[\d,]+")
  self.assertIsNone(reference_commerce_safe(raw))
 def test_old_price_cannot_override_agent_response(self):
  r=respond("Cuánto vale iPhone 14 Pro Max 256 GB negro?",
            Conversation(),self.provider,self.reference)
  self.assertEqual(r["status"],"reference_shadow")
  self.assertIn("256 GB",r["reply"])
  self.assertIn("negro",r["reply"])
  self.assertNotRegex(r["reply"],r"L\s*[\d,.]+")
  self.assertNotIn("16,700",r["reply"])
  self.assertTrue(r["human_review"])
 def test_no_unverified_financing_rate(self):
  raw=approved_reply("Quiero pagar en tarjeta a 12 meses con BAC",[])
  self.assertIn("%",raw)
  self.assertIsNone(reference_commerce_safe(raw))
 def test_no_unverified_gifts_or_guarantee(self):
  for phrase in ("A precio de lista te llevás cobertor, cargador y auriculares.",
                 "La garantía escrita es de 30 días en usados.",
                 "Te comparto la imagen de nuestras cuentas.",
                 "Ese iPhone tiene la salud de batería al 100 %."):
   with self.subTest(phrase=phrase):
    self.assertIsNone(reference_commerce_safe(phrase))
 def test_hand_off_message_is_not_accepted_as_completed(self):
  raw=approved_reply("Quiero hablar con una persona",[])
  self.assertIsNone(reference_commerce_safe(raw))
  text=safe_reference_sales_reply("Quiero hablar con una persona")
  self.assertIn("no ha sido transferida",text)
 def test_reservation_denial_not_supported_by_old_reference(self):
  raw=approved_reply("Quiero reservar el iPhone 14 Pro Max 256 GB negro",[])
  self.assertIn("No hacemos apartados",raw)
  self.assertIsNone(reference_commerce_safe(raw))
  text=safe_reference_sales_reply("Quiero reservar para mañana")
  self.assertIn("confirmar existencia",text)
 def test_provider_outage_no_old_catalog_quote(self):
  def fail(stage,ctx):
   raise ConnectionError("test-only disconnection")
  r=respond("Cuánto vale el iPhone 14 Pro Max 256 GB negro?",
    Conversation(),fail,self.reference)
  self.assertEqual(r["status"],"reference_fallback")
  self.assertEqual(r["provider_status"],"unavailable")
  self.assertNotRegex(r["reply"],r"L\s*[\d,.]+")
  self.assertNotIn("16,700",r["reply"])
  self.assertTrue(r["human_review"])
  self.assertIsNone(r["action"])
 def test_provider_outage_no_false_photo_dispatch(self):
  def fail(stage,ctx):raise ConnectionError("test outage")
  r=respond("Me enviás las fotos por favor?",
    Conversation(model=MODEL,storage_gb=256,color="Negro"),
    fail,self.reference)
  self.assertNotIn("ya envié",r["reply"].lower())
  self.assertNotIn("te comparto",r["reply"].lower())
  self.assertIsNone(r["action"])
 def test_preference_kept_in_protective_fallback(self):
  state=Conversation(model=MODEL,storage_gb=256,color="Negro",city="Choloma")
  reply=safe_reference_sales_reply("Qué precio me das",state=state)
  self.assertIn("iPhone 14 Pro Max",reply)
  self.assertIn("256 GB",reply)
  self.assertIn("negro",reply)
  self.assertNotIn("¿Qué capacidad",reply)
 def test_payment_not_auto_confirmed(self):
  q=safe_reference_sales_reply("Ya pagué por transferencia")
  self.assertIn("todavía debe comprobarse",q)
  self.assertNotIn("pago confirmado",q)
 def test_non_reference_synthetic_inventory_unchanged(self):
  from training_inventory import SimulationInventory
  from sales_ai_agent import LABEL
  data=SimulationInventory()
  def provider(stage,ctx):
   if stage=="extract":
    return {"intent":"availability","model":MODEL,"storage_gb":256,
            "color":"Negro","human_review":False}
   return {"reply":"Para ese iPhone, la versión de prueba está disponible a L 18,950."}
  r=respond("Tenés iPhone 14 Pro Max 256 GB negro?",
     Conversation(),provider,data)
  self.assertEqual(r["status"],"simulated")
  self.assertTrue(r["reply"].startswith(LABEL))

if __name__=="__main__":
 unittest.main()
