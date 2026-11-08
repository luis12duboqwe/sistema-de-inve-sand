"""Meta Ads evidence and budget protection using invented test data only."""
from datetime import datetime,timezone,timedelta
import unittest
from marketing_analytics import analyze,validate

def fake():
    return {"source":"metricool_meta_ads_read_only","business_alias":"softmobile",
      "network":"metaAds","captured_utc":datetime.now(timezone.utc).isoformat(),
      "campaigns_returned":0,"daily_rows_returned":31,
      "fields":["FAEV01","FAEV04","FAEV05"],
      "impressions_reported":"0.0","spend_reported":"0.0","clicks_reported":"0.0",
      "refresh_automated":False,"any_campaign_modified":False,
      "read_only":True,"client_sales_attributed_verified":False}
class MarketingTests(unittest.TestCase):
    def test_zero_campaign_rows_block_roas(self):
        v=analyze(fake())
        self.assertFalse(v["campaign_delivery_independently_verified"])
        self.assertFalse(v["ads_optimization_permitted"])
        self.assertFalse(v["client_sales_attributed_verified"])
        self.assertEqual(v["campaigns_returned"],0)
        self.assertFalse(v["ads_data_integrated_into_vps"])
        self.assertEqual(v["campaigns_modified"],0)
    def test_positive_numbers_still_cannot_spend(self):
        x=fake()
        x.update({"campaigns_returned":2,"impressions_reported":"2500.00",
                  "clicks_reported":"125","spend_reported":"300"})
        v=analyze(x)
        self.assertTrue(v["performance_data_present"])
        self.assertFalse(v["ads_optimization_permitted"])
        self.assertFalse(v["campaign_delivery_independently_verified"])
    def test_stale_source_rejected(self):
        x=fake();x["captured_utc"]=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
        with self.assertRaises(ValueError):validate(x)
    def test_future_capture_rejected(self):
        x=fake();x["captured_utc"]=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):validate(x)
    def test_wrong_network_rejected(self):
        x=fake();x["network"]="googleAds"
        with self.assertRaises(ValueError):validate(x)
    def test_missing_field_rejected(self):
        x=fake();x["fields"]=["FAEV01","FAEV04"]
        with self.assertRaises(ValueError):validate(x)
    def test_negative_spend_rejected(self):
        x=fake();x["spend_reported"]="-1"
        with self.assertRaises(ValueError):validate(x)
    def test_non_finite_rejected(self):
        x=fake();x["clicks_reported"]="NaN"
        with self.assertRaises(ValueError):validate(x)
    def test_paid_action_rejected(self):
        x=fake();x["any_campaign_modified"]=True
        with self.assertRaises(ValueError):validate(x)
    def test_improper_types_rejected(self):
        x=fake();x["campaigns_returned"]=False
        with self.assertRaises(ValueError):validate(x)
    def test_unverified_attribution_rejected(self):
        x=fake();x["client_sales_attributed_verified"]=True
        with self.assertRaises(ValueError):validate(x)

if __name__=="__main__":
    unittest.main()
