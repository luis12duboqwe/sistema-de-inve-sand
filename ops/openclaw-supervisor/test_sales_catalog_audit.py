"""Sales catalog quality checks: no customer, price, SKU or database writes."""
import json,types,unittest
from unittest.mock import Mock
import sales_catalog_audit as c
def fixture():
 return dict(active_products=189,stocked_active_products=54,
  stocked_fully_specified=53,active_no_model=0,active_no_color=1,
  active_no_capacity=0,active_no_price=0,active_no_cost=0,
  active_price_below_cost=3,active_non_hnl=0,stocked_in_inactive_locations=0)
class CatalogTests(unittest.TestCase):
 def test_count_aggregation(self):
  d=c.report(fixture(),now="2026-11-09T00:00:00+00:00")
  self.assertEqual(d["counts"]["active_without_stock"],135)
  self.assertEqual(d["counts"]["stocked_missing_required_quote_fields"],1)
  self.assertEqual(d["counts"]["active_price_below_cost"],3)
 def test_no_unsafe_quote_authorization(self):
  d=c.report(fixture())
  for k in ("outbound_customer_quote_authorized","partner_stock_connected",
            "stock_freshness_verified","price_freshness_verified",
            "inventory_updated","raw_price_or_cost_extracted",
            "customer_data_extracted","public_release_permitted"):
   self.assertFalse(d[k])
  self.assertEqual(d["public_messages_sent"],0)
 def test_rejects_missing_and_extra_columns(self):
  for value in ({"active_products":1},{**fixture(),"pii":"name"}):
   with self.assertRaises(c.Reject):c.validate(value)
 def test_rejects_boolean_counts_and_negative(self):
  for key in ("active_products","stocked_active_products","active_price_below_cost"):
   d=fixture();d[key]=True
   with self.assertRaises(c.Reject):c.validate(d)
   d[key]=-1
   with self.assertRaises(c.Reject):c.validate(d)
 def test_rejects_impossible_coverage(self):
  d=fixture();d["stocked_fully_specified"]=55
  with self.assertRaises(c.Reject):c.validate(d)
 def test_only_read_only_sql(self):
  self.assertIn("BEGIN TRANSACTION READ ONLY",c.SQL)
  self.assertIn("ROLLBACK",c.SQL)
  self.assertNotIn("UPDATE ",c.SQL)
  self.assertNotIn("DELETE ",c.SQL)
  self.assertNotIn("INSERT ",c.SQL)
 def test_mock_runner_is_fixed_no_credentials(self):
  called=[]
  def fake(cmd,**kwargs):
   called.append((cmd,kwargs))
   return types.SimpleNamespace(returncode=0,
      stdout=c.MARK+json.dumps(fixture())+"\n",stderr="")
  x=c.query(runner=fake)
  self.assertEqual(x["active_products"],189)
  cmd,kw=called[0]
  self.assertEqual(cmd[:4],["runuser","-u","postgres","--"])
  self.assertEqual(cmd[-2:],["-d","inventory_db"])
  self.assertIn("READ ONLY",kw["input"])
 def test_fail_closed_when_db_unavailable(self):
  with self.assertRaises(c.Reject):
   c.query(runner=lambda *a,**k:types.SimpleNamespace(
     returncode=1,stdout="",stderr="unavailable"))
 def test_no_actual_price_values_in_report(self):
  text=json.dumps(c.report(fixture()))
  self.assertNotIn("precio",text)
  self.assertNotIn("imei",text)
  self.assertNotIn("telefono",text)
if __name__=="__main__":
 unittest.main()
