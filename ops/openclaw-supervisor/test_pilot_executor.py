"""Regression tests for SoftMobile's prelaunch internal action executor."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch

import pilot_executor as p

def data():
    now=datetime.now(timezone.utc).isoformat()
    sup={"captured_utc":now,"mode":"read_only","public_messages_sent":0,
         "production_changed":False,
         "chatwoot":{"coverage_complete":True,"redacted":True,
                     "queues":{"unanswered":[2],"recoverable":[]}},
         "release_gates":{"public_messaging_ready":False},
         "quality":{"all_local_tests_passed":True,"independent_convergence":False},
         "health":{"all_containers_running":True,"whatsapp_online":False,
                   "disk_free_percent":77,"memory_available_percent":48}}
    task=lambda tid,evidence=None,status="review":{
        "id":tid,"area":"ventas" if tid.startswith("ventas_") else "operaciones",
        "priority":"alta","status":status,"requires_approval":True,
        "automatic_external_actions":0,"owner":"humano",
        "evidence":evidence or {}}
    director={"schema_version":1,"mode":"proposals_only","source_utc":now,
              "production_changed":False,"public_messages_sent":0,
              "specialists":{"ventas":1,"operaciones":1},
              "tasks":[task("ventas_respuestas",{"conversation_ids":[2]}),
                       task("ventas_despliegue",{"blockers":["offline"]},"blocked")]}
    return sup,director

class PilotExecutorTests(unittest.TestCase):
    def input_pair(self,**changes):
        sup,director=data()
        sup.update(changes.get("supervisor",{}))
        director.update(changes.get("director",{}))
        return sup,director

    def put(self,root,sup,director):
        (root/"latest.json").write_text(json.dumps(sup))
        (root/"DIRECTOR.json").write_text(json.dumps(director))

    def test_safe_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.put(root,*data())
            s,d=p.load_inputs(root)
            self.assertEqual(d["source_utc"],s["captured_utc"])

    def test_stale(self):
        sup,director=data()
        dt=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        sup["captured_utc"]=director["source_utc"]=dt
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_mismatched_sources(self):
        sup,director=data();director["source_utc"]="2026-01-01T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_no_public_message(self):
        sup,director=data();sup["public_messages_sent"]=1
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_unapproved_release(self):
        sup,director=data();sup["release_gates"]["public_messaging_ready"]=True
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_mutation_flag(self):
        sup,director=data();director["production_changed"]=True
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_unallowlisted_task(self):
        sup,director=data();director["tasks"][0]["id"]="systemctl restart waha"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_duplicate_task(self):
        sup,director=data();director["tasks"].append(director["tasks"][0].copy())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_external_action_guard(self):
        sup,director=data();director["tasks"][0]["automatic_external_actions"]=1
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_false_approval_flag(self):
        sup,director=data();director["tasks"][0]["requires_approval"]=False
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.put(root,sup,director)
            with self.assertRaises(p.Reject):p.load_inputs(root)

    def test_blocked_task_never_runs(self):
        sup,director=data()
        state,detail=p.safe_action(director["tasks"][1],sup,{})
        self.assertEqual(state,"blocked")

    def test_safe_sales_simulation_result_internal(self):
        sup,director=data()
        t={**director["tasks"][0],"id":"ventas_simulaciones",
           "evidence":{"scenarios":72,"passed":72,"failed":0,"synthetic_only":True}}
        st,detail=p.safe_action(t,sup,{})
        self.assertEqual(st,"checked_needs_review")
        self.assertEqual(detail["verified_real_sales"],0)

    def test_sales_simulation_regression_escalates(self):
        sup,director=data()
        t={**director["tasks"][0],"id":"ventas_simulaciones",
           "evidence":{"scenarios":72,"passed":71,"failed":1,"synthetic_only":True}}
        st,_=p.safe_action(t,sup,{})
        self.assertEqual(st,"needs_attention")

    def test_sales_simulation_inconsistent_counts_rejected(self):
        sup,director=data()
        t={**director["tasks"][0],"id":"ventas_simulaciones",
           "evidence":{"scenarios":72,"passed":72,"failed":2,"synthetic_only":True}}
        with self.assertRaises(p.Reject):p.safe_action(t,sup,{})

    def test_lead_is_internal(self):
        sup,director=data()
        state,detail=p.safe_action(director["tasks"][0],sup,{})
        self.assertEqual(state,"awaiting_human")
        self.assertEqual(detail["pilot_conversation_ids"],[2])

    def test_invalid_lead_refused(self):
        sup,director=data()
        director["tasks"][0]["evidence"]["conversation_ids"]=[999]
        with self.assertRaises(p.Reject):
            p.safe_action(director["tasks"][0],sup,{})

    def test_idempotent_task_db(self):
        sup,director=data()
        with sqlite3.connect(":memory:") as con:
            p.init_db(con)
            first=p.execute(sup,director,con)
            second=p.execute(sup,director,con)
            self.assertEqual(first["checked"],2)
            self.assertEqual(second["checked"],2)
            self.assertEqual(second["tasks"][0]["checks"],2)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],2)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM cycles").fetchone()[0],2)
            self.assertEqual(second["external_actions"],0)
            self.assertEqual(second["public_messages_sent"],0)

    def test_finance_and_stock_share_one_read(self):
        sup,director=data()
        stock={"negative_stock":0,"out_of_stock_products":135,
               "completed_orders":0,"validated_orders":0,
               "orders_by_state":{"pendiente":458},
               "transfers_by_state":{"confirmada":62}}
        t=director["tasks"][0]
        director["tasks"]=[
          {**t,"id":"finanzas_no_conciliadas","area":"finanzas"},
          {**t,"id":"inventario_sin_stock","area":"inventario"},
          {**t,"id":"inventario_transferencias","area":"inventario"}
        ]
        with sqlite3.connect(":memory:") as con,patch.object(p,"read_inventory",return_value=stock) as source:
            p.init_db(con)
            out=p.execute(sup,director,con)
            source.assert_called_once()
        self.assertEqual(out["checked"],3)
        self.assertEqual(out["failures"],0)
        self.assertIn("pendiente",out["tasks"][0]["details"]["orders_by_state"])

    def test_stock_read_failure_marked_not_success(self):
        sup,director=data()
        t=director["tasks"][0]
        director["tasks"]=[{**t,"id":"inventario_sin_stock","area":"inventario"}]
        with sqlite3.connect(":memory:") as con,patch.object(p,"read_inventory",side_effect=p.Reject("offline")):
            p.init_db(con);out=p.execute(sup,director,con)
        self.assertEqual(out["failures"],1)
        self.assertEqual(out["tasks"][0]["state"],"needs_attention")

    def test_photo_check_uses_only_ids(self):
        sup,director=data()
        t=director["tasks"][0]
        director["tasks"]=[{**t,"id":"operaciones_fotos","evidence":{"request_ids":[1]}}]
        with patch.object(p,"read_photo",return_value=[{"request_id":1,"status":"pending"}]) as f:
            st,details=p.safe_action(director["tasks"][0],sup,{})
            f.assert_called_once_with([1])
        self.assertEqual(st,"awaiting_human")
        self.assertNotIn("customer_name",str(details))

    def test_wa_health_only_read(self):
        sup,director=data();t=director["tasks"][0]
        t={**t,"id":"infraestructura_waha_piloto"}
        with patch.object(p,"containers",return_value={"WAHA":"exited"}):
            state,info=p.safe_action(t,sup,{})
        self.assertEqual(info["pilot_container_states"]["WAHA"],"exited")
        self.assertEqual(state,"checked_needs_review")

    def test_test_suite_fixed_argv_and_cwd(self):
        class Fake:
            returncode=0
            stderr="Ran 62 tests in 0.02s\n\nOK\n"
            stdout=""
        with patch.object(p.subprocess,"run",return_value=Fake()) as run:
            out=p.code_tests()
        args,kw=run.call_args
        self.assertEqual(args[0][:4],["/usr/bin/python3","-m","unittest","discover"])
        self.assertEqual(kw["cwd"],"/opt/openclaw-lab/supervisor")
        self.assertEqual(out["tests_verified"],62)
        self.assertTrue(out["passed"])

    def test_source_sql_readonly(self):
        self.assertIn("BEGIN TRANSACTION READ ONLY;",p.SQL)
        self.assertNotIn("UPDATE ",p.SQL)
        self.assertNotIn("DELETE FROM",p.SQL)

    def test_queue_report_without_private_text(self):
        sup,director=data()
        with sqlite3.connect(":memory:") as con:
            p.init_db(con)
            out=p.execute(sup,director,con)
        md=p.markdown(out)
        self.assertIn("Envíos al público: 0",md)
        self.assertNotIn("customer_name",md)
        self.assertNotIn("conversation_ids",md)

if __name__=="__main__":
    unittest.main()
