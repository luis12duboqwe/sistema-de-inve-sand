"""Read-only finance risk signals; tests use only synthetic aggregates."""
import copy
import unittest
from unittest.mock import patch

import finance_audit as f

def sample():
    return {name:0 for name in f.COUNTS}|{
      "orders":458,"orders_by_state":{"pendiente":458},
      "order_total_item_mismatch":173,
      "mismatch_by_payment":{"efectivo":6,"transferencia":14,
                             "tarjeta":96,"financiamiento":57},
      "products_price_below_cost":3,
      "products_active_out_of_stock":135
    }

class FinancialAuditTests(unittest.TestCase):
    def test_pending_orders_not_earnings(self):
        out=f.analyze(sample())
        self.assertFalse(out["revenue_verified"])
        self.assertFalse(out["profit_verified"])
        self.assertFalse(out["financial_reconciliation_prerequisites"])
        self.assertTrue(out["pending_orders_not_revenue"])
        self.assertEqual(out["raw_customer_records"],0)
        self.assertEqual(out["public_messages_sent"],0)
        self.assertEqual(out["payments_initiated"],0)
    def test_exact_diagnostics(self):
        out=f.analyze(sample())
        self.assertEqual(out["flag_count"],2)
        self.assertEqual({x["code"]:x["count"] for x in out["flags"]},
            {"order_total_item_mismatch":173,"products_price_below_cost":3})
    def test_require_validated_completed_and_approved(self):
        row=sample();row.update({"orders_completed":3,"approved_closes":1,
                                   "daily_closes":1,"orders_validated":3,
                                   "order_total_item_mismatch":0,
                                   "mismatch_by_payment":{},
                                   "recent_completed_orders_7d":3})
        out=f.analyze(row)
        self.assertTrue(out["financial_reconciliation_prerequisites"])
        self.assertFalse(out["profit_verified"])
        self.assertFalse(out["revenue_verified"])
    def test_orphan_records_flagged_critical(self):
        row=sample();row["orphan_order_items"]=2
        out=f.analyze(row)
        self.assertEqual([x for x in out["flags"] if x["code"]=="orphan_order_items"][0]["severity"],"CRITICAL")
    def test_mismatched_status_totals_rejected(self):
        row=sample();row["orders_by_state"]["pendiente"]=457
        with self.assertRaises(ValueError):f.validate(row)
    def test_negative_counts_rejected(self):
        row=sample();row["stock_negative_rows"]=-1
        with self.assertRaises(ValueError):f.validate(row)
    def test_boolean_count_rejected(self):
        row=sample();row["orders_completed"]=True
        with self.assertRaises(ValueError):f.validate(row)
    def test_close_consistency_rejected(self):
        row=sample();row["approved_closes"]=1
        with self.assertRaises(ValueError):f.validate(row)
    def test_completed_consistency_rejected(self):
        row=sample();row["orders_completed"]=459
        with self.assertRaises(ValueError):f.validate(row)
    def test_count_retains_data_not_buyer(self):
        r=f.analyze(sample())
        serialized=__import__("json").dumps(r)
        for forbidden in ('"customer_name":','"customer_phone":','"transfer_reference":',
                          '"customer_id":','"bank_account":','"payment_details":'):
            self.assertNotIn(forbidden,serialized)
    def test_sql_has_read_only_transaction(self):
        self.assertIn("BEGIN TRANSACTION READ ONLY;",f.QUERY)
        self.assertIn("COMMIT;",f.QUERY)
        self.assertNotIn("UPDATE orders SET",f.QUERY)
        self.assertNotIn("DELETE FROM orders",f.QUERY)
    def test_markdown_disclaims_real_revenue(self):
        md=f.markdown(f.analyze(sample()))
        self.assertIn("Ingresos verificados: NO",md)
        self.assertIn("Utilidad verificada: NO",md)

if __name__=="__main__":
    unittest.main()
