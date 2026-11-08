"""Offline regression tests for the eight-domain SoftMobile director."""
import json
import hashlib
import tempfile
from pathlib import Path
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import director as d

def snapshot(**changes):
    now=datetime.now(timezone.utc).isoformat()
    x={"mode":"read_only","production_changed":False,"public_messages_sent":0,
       "captured_utc":now,
       "chatwoot":{"status":"ok","coverage_complete":True,"redacted":True,
                   "queues":{"unanswered":[2],"recoverable":[]}},
       "release_gates":{"public_messaging_ready":False,
                        "blockers":["pilot_transport_online","independent_qa_converged"]},
       "followups":{"mode":"proposals_only","cases":[]},
       "inventory":{"status":"ok","orders_pending":458,
                    "out_of_stock_active_products":135,"available_units":106},
       "photos":{"older_than_2h_pending_review_ids":[1]},
       "quality":{"all_local_tests_passed":True,"independent_convergence":False,
                  "tests":492},
       "health":{"whatsapp_online":False,"all_containers_running":True,
                 "memory_available_percent":45.2,"disk_free_percent":77.0}}
    return x | changes

def metrics():
    return {"orders_completed":0,"daily_closes":0,"stock_transfers":62,
            "transfers_by_state":{"confirmada":62}}

class DirectorTests(unittest.TestCase):
    def test_broad_domains(self):
        res=d.plan(snapshot(),metrics())
        self.assertEqual(set(res["specialists"]),set(d.AREAS))
        self.assertTrue(all(res["specialists"][k]>0 for k in d.AREAS))
    def test_never_sends(self):
        res=d.plan(snapshot(),metrics())
        self.assertEqual(res["public_messages_sent"],0)
        self.assertFalse(res["production_changed"])
        self.assertTrue(all(t["automatic_external_actions"]==0 and
                            t["requires_approval"] for t in res["tasks"]))
    def test_stock_not_auto_purchase(self):
        res=d.plan(snapshot(),metrics())
        t=next(t for t in res["tasks"] if t["id"]=="inventario_sin_stock")
        self.assertEqual(t["evidence"]["active_products_without_stock"],135)
        self.assertIn("no comprar",t["next_action"])
    def test_fictional_sales_conversion_is_not_real_sale(self):
        conversion={"available":True,"scenarios":72,"passed":72,"failed":0,
                    "synthetic_only":True}
        res=d.plan(snapshot(),metrics(),conversion=conversion)
        item=next(t for t in res["tasks"] if t["id"]=="ventas_simulaciones")
        self.assertEqual(item["evidence"]["scenarios"],72)
        self.assertTrue(item["requires_approval"])
        self.assertEqual(item["automatic_external_actions"],0)
        self.assertFalse(res["verified_finance"]["profit_verified"])

    def test_conversion_failure_is_high_priority(self):
        conversion={"available":True,"scenarios":72,"passed":71,"failed":1}
        res=d.plan(snapshot(),metrics(),conversion=conversion)
        item=next(t for t in res["tasks"] if t["id"]=="ventas_simulaciones")
        self.assertEqual(item["priority"],"alta")

    def test_sales_simulation_source_hash_is_required(self):
        with tempfile.TemporaryDirectory() as folder:
            bot=Path(folder)/"bot.rb"
            bot.write_text("pilot ruby content")
            result_path=Path(folder)/"report.json"
            report={
                "at":datetime.now(timezone.utc).isoformat(),
                "environment":"OFFLINE_TRAINING_ONLY",
                "public_messages_sent":0,"real_orders":0,
                "real_inventory_modified":False,"is_live_source":True,
                "scored_source_sha256":"incorrect-old-source-hash",
                "scenarios":72,"passed":72,"failed":0,
                "by_family":{"purchase":{"passed":72,"tested":72}}
            }
            result_path.write_text(json.dumps(report))
            fake=lambda value:result_path if str(value).endswith("sales-conversion-training-report.json") else bot
            with patch.object(d,"Path",side_effect=fake):
                self.assertEqual(d.sales_simulation_snapshot()["reason"],"source_drift")
                report["scored_source_sha256"]=hashlib.sha256(bot.read_bytes()).hexdigest()
                result_path.write_text(json.dumps(report))
                self.assertTrue(d.sales_simulation_snapshot()["available"])

    def test_missing_sales_simulations_not_invented(self):
        res=d.plan(snapshot(),metrics(),conversion={"available":False})
        self.assertNotIn("ventas_simulaciones",{t["id"] for t in res["tasks"]})

    def test_synthetic_replay_stays_advisory(self):
        qa={"available":True,"synthetic_issues":250,"replayed":250,
            "outcomes":{"previous_flags_reproduced":202,"ai_only_still_unverified":38,
                        "previous_flags_no_longer_present":10}}
        res=d.plan(snapshot(),metrics(),qa)
        t=next(t for t in res["tasks"] if t["id"]=="calidad_replay_aislado")
        self.assertEqual(t["evidence"]["synthetic_replayed"],250)
        self.assertEqual(t["automatic_external_actions"],0)
        self.assertIn("hipótesis",t["next_action"])
        self.assertTrue(res["synthetic_qa"]["available"])

    def test_synthetic_qa_bad_inputs_do_not_claim_results(self):
        out=d.plan(snapshot(),metrics(),{"available":False,"reason":"stale"})
        self.assertNotIn("calidad_replay_aislado",{t["id"] for t in out["tasks"]})

    def test_zero_completed_not_profits(self):
        res=d.plan(snapshot(),metrics())
        self.assertFalse(res["verified_finance"]["profit_verified"])
        self.assertEqual(res["verified_finance"]["completed_orders"],0)
    def test_no_finance_completion_when_unavailable(self):
        res=d.plan(snapshot(),{})
        self.assertIsNone(res["verified_finance"]["completed_orders"])
    def test_repair_is_blocked(self):
        res=d.plan(snapshot(),metrics())
        self.assertEqual(next(t for t in res["tasks"] if t["id"]=="operaciones_reparaciones")["status"],"blocked")
    def test_ads_source_not_invented(self):
        res=d.plan(snapshot(),metrics())
        self.assertEqual(next(t for t in res["tasks"] if t["id"]=="publicidad_sin_fuente")["status"],"blocked")
    def test_transfer_confirmed_not_pending_assertion(self):
        res=d.plan(snapshot(),metrics())
        t=next(t for t in res["tasks"] if t["id"]=="inventario_transferencias")
        self.assertIn("no interpretar",t["next_action"])
    def test_duplicate_ids_are_stable(self):
        x=d.plan(snapshot(),metrics())
        y=d.plan(snapshot(),metrics())
        self.assertEqual([t["id"] for t in x["tasks"]],[t["id"] for t in y["tasks"]])
        self.assertEqual(len({t["id"] for t in x["tasks"]}),len(x["tasks"]))
    def test_consented_cases_still_manual(self):
        r=snapshot(followups={"mode":"proposals_only","cases":[{"conversation_id":4,
                         "quote_id":30,"status":"ready_for_manual_review"}]})
        t=next(t for t in d.plan(r,metrics())["tasks"] if t["id"]=="ventas_seguimiento")
        self.assertTrue(t["requires_approval"])
        self.assertEqual(t["automatic_external_actions"],0)
    def test_stale(self):
        dt=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        with self.assertRaises(d.Reject):d.plan(snapshot(captured_utc=dt),metrics())
    def test_future_timestamp(self):
        dt=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
        with self.assertRaises(d.Reject):d.plan(snapshot(captured_utc=dt),metrics())
    def test_unapproved_messaging_release(self):
        with self.assertRaises(d.Reject):
            d.plan(snapshot(release_gates={"public_messaging_ready":True}),metrics())
    def test_incomplete_coverage(self):
        with self.assertRaises(d.Reject):
            d.plan(snapshot(chatwoot={"coverage_complete":False,"redacted":True}),metrics())
    def test_private_message_data_not_allowed(self):
        with self.assertRaises(d.Reject):
            d.plan(snapshot(chatwoot={"coverage_complete":True,"redacted":False}),metrics())
    def test_side_effect_guard(self):
        with self.assertRaises(d.Reject):
            d.plan(snapshot(public_messages_sent=1),metrics())
    def test_no_unverified_missing_stock_claims(self):
        x=snapshot(inventory={"status":"unavailable"})
        res=d.plan(x,metrics())
        self.assertNotIn("inventario_sin_stock",{t["id"] for t in res["tasks"]})
    def test_no_unanswered_when_queue_empty(self):
        c=snapshot()["chatwoot"] | {"queues":{"unanswered":[]}}
        x=snapshot(chatwoot=c)
        self.assertNotIn("ventas_respuestas",{t["id"] for t in d.plan(x,metrics())["tasks"]})
    def test_sql_read_only(self):
        self.assertIn("BEGIN TRANSACTION READ ONLY;",d.SQL)
        self.assertNotIn("UPDATE orders",d.SQL)
        self.assertNotIn("DELETE FROM",d.SQL)
    def test_report_contains_no_full_messages(self):
        out=d.plan(snapshot(),metrics())
        txt=d.markdown(out)
        self.assertNotIn("customer_phone",txt)
        self.assertIn("Mensajes a clientes: 0",txt)
    def test_output_schema_json_serializable(self):
        json.dumps(d.plan(snapshot(),metrics()),ensure_ascii=False)
    def test_explicit_approval_always(self):
        res=d.plan(snapshot(),metrics())
        self.assertTrue(all(t["owner"]=="humano" for t in res["tasks"]))

if __name__=="__main__":
    unittest.main()
