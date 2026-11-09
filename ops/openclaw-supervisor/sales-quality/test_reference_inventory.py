#!/usr/bin/env python3
"""Trusted reference-catalog tests; zero real inventory and zero outbound sends."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from reference_inventory import ReferenceCatalog,ReferenceCatalogError,SOURCE_ID
from sales_ai_agent import Conversation,respond,grounded_reply,AgentBlocked

class ReferenceTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.catalog=ReferenceCatalog()
 def make(self,message,model="iPhone 14 Pro Max",gb=256,color="Negro",intent="price",
          reply="Un asesor debe confirmar el precio y las existencias."):
  def provider(stage,data):
   if stage=="extract":
    return {"intent":intent,"model":model,"storage_gb":gb,
            "color":color,"human_review":True}
   return {"reply":reply}
  return respond(message,Conversation(),provider,self.catalog)
 def test_reference_is_not_live_inventory(self):
  self.assertGreaterEqual(len(self.catalog.catalog()),50)
  f=self.catalog.fact("iPhone 14 Pro Max",256,"Negro")
  self.assertEqual(f["status"],"unverified")
  self.assertFalse(f["stock_verified"])
  self.assertFalse(f["color_verified"])
  self.assertFalse(f["price_verified"])
  self.assertTrue(f["catalog_model_capacity_listed"])
  self.assertIsNone(f["variant"])
 def test_price_reference_cannot_be_quoted(self):
  r=self.make("iPhone 14 Pro Max 256 GB negro cuánto vale?",
              reply="Te cuesta L 18,950.")
  self.assertEqual(r["status"],"reference_shadow")
  self.assertTrue(r["human_review"])
  self.assertNotIn("18,950",r["reply"])
  self.assertIn("verificar precio vigente",r["reply"])
  self.assertIn("256 GB",r["reply"])
  self.assertNotIn("asesor",r["reply"])
 def test_suffix_currency_must_be_blocked(self):
  r=self.make("Quiero iPhone 14 Pro Max 256 GB negro",
              reply="Sale 18950 LPS y lo tenemos en existencia.")
  self.assertNotIn("18950",r["reply"])
  self.assertTrue(r["human_review"])
 def test_bare_price_blocked_without_verified_source(self):
  r=self.make("Cuánto vale iPhone 14 Pro Max 256 GB negro?",
              reply="Ese modelo sale 18950.")
  self.assertNotIn("18950",r["reply"])
  self.assertTrue(r["human_review"])
 def test_unverified_available_claim_blocked(self):
  r=self.make("Está disponible el iPhone 14 Pro Max 256 GB negro?",
              reply="Sí, está disponible.")
  self.assertNotIn("está disponible",r["reply"].lower())
  self.assertTrue(r["human_review"])
 def test_promised_followup_blocked(self):
  r=self.make("Quiero fotos del iPhone 14 Pro Max 256 GB negro",
              intent="photos",reply="Ya solicité fotos; en cuanto tenga respuesta, te aviso.")
  self.assertNotIn("te aviso",r["reply"].lower())
  self.assertIsNone(r["action"])
 def test_unlisted_gb_not_claimed(self):
  f=self.catalog.fact("iPhone 14 Pro Max",1024,"Azul")
  self.assertFalse(f["catalog_model_capacity_listed"])
 def test_photo_proposal_without_dispatch(self):
  r=self.make("Podés mandarme fotos del iPhone 14 Pro Max 256 GB negro?",
              intent="photos",reply="Puedo solicitar fotos al encargado, aún no están verificadas.")
  self.assertEqual(r["action"],"photo_request_proposal")
  self.assertFalse(r["tool"]["stock_verified"])
  self.assertNotIn("SIMULACIÓN",r["reply"])
 def test_missing_model_requires_human(self):
  r=self.make("Quiero Nokia G80 256 GB",model="Nokia G80")
  self.assertEqual(r["status"],"needs_human")
  self.assertTrue(r["human_review"])
 def test_snapshot_rejects_claimed_stock(self):
  with tempfile.TemporaryDirectory() as tmp:
   from reference_inventory import DEFAULT
   data=json.loads(DEFAULT.read_text())
   data["approved_for_stock"]=True
   target=Path(tmp)/"ref.json";target.write_text(json.dumps(data))
   with self.assertRaises(ReferenceCatalogError):ReferenceCatalog(target)
 def test_snapshot_rejects_price_field(self):
  with tempfile.TemporaryDirectory() as tmp:
   from reference_inventory import DEFAULT
   data=json.loads(DEFAULT.read_text())
   data["variants"][0]["price"]=100
   target=Path(tmp)/"ref.json";target.write_text(json.dumps(data))
   with self.assertRaises(ReferenceCatalogError):ReferenceCatalog(target)

if __name__=="__main__":unittest.main()
