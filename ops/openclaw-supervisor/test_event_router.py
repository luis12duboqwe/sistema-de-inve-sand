"""Off-network replay tests for the internal OpenClaw event router."""
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch

from pilot_executor import Reject
import event_router as e

def fixtures():
    utc=datetime.now(timezone.utc).isoformat()
    supervisor={"captured_utc":utc,"mode":"read_only",
      "public_messages_sent":0,"production_changed":False,
      "chatwoot":{"coverage_complete":True,"redacted":True},
      "release_gates":{"public_messaging_ready":False}}
    x={"id":"ventas_respuestas","area":"ventas","priority":"alta",
       "status":"review","requires_approval":True,"automatic_external_actions":0,
       "owner":"humano","evidence":{"conversation_ids":[2]}}
    dir={"schema_version":1,"mode":"proposals_only","source_utc":utc,
         "production_changed":False,"public_messages_sent":0,
         "specialists":{"ventas":1},"tasks":[x]}
    op={"schema_version":1,"mode":"internal_actions_only","at":utc,
        "source_utc":utc,"checked":1,"failures":0,
        "public_messages_sent":0,"external_actions":0,
        "production_changed":False,"public_messaging_enabled":False,
        "approval_required_for_all_external_actions":True,
        "tasks":[{"id":"ventas_respuestas","state":"awaiting_human",
         "priority":"alta","checks":1,"details":{"pilot_conversation_ids":[2]},
         "requires_human_approval":True}]}
    return supervisor,dir,op

def prepare(root,sup,director,operator):
    for fname,body in [("latest.json",sup),("DIRECTOR.json",director),
                       ("OPERATOR.json",operator)]:
        (root/fname).write_text(json.dumps(body))

class EventRouterTests(unittest.TestCase):
    def test_detect_once_no_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prepare(root,*fixtures())
            a=e.run(root)
            b=e.run(root)
            self.assertEqual(len(a["events"]),1)
            self.assertEqual(len(b["events"]),0)
            self.assertEqual(b["queued"],1)
            self.assertEqual(b["public_messages_sent"],0)
            self.assertEqual(b["external_commercial_actions"],0)
            with sqlite3.connect(root/"events.sqlite3") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0],1)
                self.assertEqual(db.execute("SELECT change_count FROM work_items").fetchone()[0],1)
    def test_changed_on_meaningful_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            sup,d,op=fixtures();prepare(root,sup,d,op)
            e.run(root)
            op["tasks"][0]["details"]["pilot_conversation_ids"]=[2,4]
            prepare(root,sup,d,op)
            result=e.run(root)
            self.assertEqual(result["events"][0]["event"],"changed")
    def test_rolling_counter_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            sup,d,op=fixtures();prepare(root,sup,d,op)
            e.run(root)
            op["tasks"][0]["checks"]=100
            prepare(root,sup,d,op)
            self.assertEqual(len(e.run(root)["events"]),0)
    def test_not_observed_does_not_mark_complete(self):
        with sqlite3.connect(":memory:") as db:
            e.db_setup(db)
            _,d,op=fixtures()
            e.changes(db,d,{r["id"]:r for r in op["tasks"]},"2026-11-07T00:00:00+00:00")
            events=e.changes(db,{"tasks":[]},{}, "2026-11-07T00:01:00+00:00")
            self.assertEqual(events[0]["event"],"not_observed")
            self.assertEqual(e.queue(db)[0]["state"],"not_in_current_snapshot")
            self.assertEqual(len(e.changes(db,{"tasks":[]},{},
                                           "2026-11-07T00:02:00+00:00")),0)
    def test_reappeared_is_detected_after_missing_snapshot(self):
        with sqlite3.connect(":memory:") as db:
            e.db_setup(db)
            _,d,op=fixtures()
            rows={row["id"]:row for row in op["tasks"]}
            e.changes(db,d,rows,"2026-11-07T00:00:00+00:00")
            e.changes(db,{"tasks":[]},{},"2026-11-07T00:01:00+00:00")
            events=e.changes(db,d,rows,"2026-11-07T00:02:00+00:00")
            self.assertEqual(events[0]["event"],"reappeared")

    def test_partial_scope_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            sup,d,op=fixtures();op["checked"]=0
            prepare(root,sup,d,op)
            with self.assertRaises(Reject):e.validate_inputs(root)
    def test_unknown_task_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sup,d,op=fixtures()
            op["tasks"][0]["id"]="DROP TABLE customers"
            prepare(root,sup,d,op)
            with self.assertRaises(Reject):e.validate_inputs(root)
    def test_public_flag_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sup,d,op=fixtures()
            op["public_messaging_enabled"]=True
            prepare(root,sup,d,op)
            with self.assertRaises(Reject):e.validate_inputs(root)
    def test_external_action_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sup,d,op=fixtures()
            op["external_actions"]=1
            prepare(root,sup,d,op)
            with self.assertRaises(Reject):e.validate_inputs(root)
    def test_failed_operator_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sup,d,op=fixtures()
            op["failures"]=1
            prepare(root,sup,d,op)
            with self.assertRaises(Reject):e.validate_inputs(root)
    def test_stale_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sup,d,op=fixtures()
            dt=(datetime.now(timezone.utc)-timedelta(hours=3)).isoformat()
            sup["captured_utc"]=d["source_utc"]=op["source_utc"]=dt
            prepare(root,sup,d,op)
            with self.assertRaises(Reject):e.validate_inputs(root)
    def test_private_information_not_replicated(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            sup,d,op=fixtures()
            d["tasks"][0]["evidence"]["secret_customer_name"]="DO_NOT_COPY_THIS_NAME"
            prepare(root,sup,d,op)
            res=e.run(root)
            self.assertNotIn("DO_NOT_COPY_THIS_NAME",(root/"EVENTS.json").read_text())
            self.assertNotIn("DO_NOT_COPY_THIS_NAME",(root/"EVENTS.md").read_text())
            self.assertEqual(res["queued"],1)
    def test_dispatch_eligibility_requires_new_actionable_event(self):
        with sqlite3.connect(":memory:") as db:
            e.db_setup(db)
            now=datetime.now(timezone.utc).isoformat()
            record={"priority":"alta","state":"awaiting_human","role":"ventas","event":"changed"}
            self.assertTrue(e.should_dispatch(db,[record],now))
            self.assertFalse(e.should_dispatch(db,[{"priority":"baja","state":"awaiting_human"}],now))
            self.assertFalse(e.should_dispatch(db,[{"priority":"alta","state":"blocked","role":"ventas","event":"changed"}],now))
    def test_daily_dispatch_cap(self):
        with sqlite3.connect(":memory:") as db:
            e.db_setup(db)
            dt=datetime.now(timezone.utc).isoformat()
            for _ in range(e.MAX_EVENT_DISPATCHES_PER_DAY):
                db.execute("INSERT INTO dispatch(day,issued,status) VALUES(?,?,?)",
                           (dt[:10],dt,"enqueued"))
            self.assertFalse(e.should_dispatch(db,[{"priority":"alta",
                                "state":"awaiting_human","role":"ventas","event":"changed"}],dt))
    def test_allowlisted_agent_job(self):
        self.assertEqual(e.ROLE_JOB_IDS["ventas"],"d70dd8ed-eb9f-451c-9e40-067da8ed3a6c")
        class P:
            returncode=0
            def __init__(self,stdout):
                self.stdout=stdout
        job={"id":e.ROLE_JOB_IDS["ventas"],"enabled":True,"sessionTarget":"isolated",
             "payload":{"kind":"agentTurn","toolsAllow":["read","write"]},
             "delivery":{"mode":"none"}}
        with patch.object(e.subprocess,"run",side_effect=[
               P(json.dumps({"jobs":[job]})),P('{"ok":true,"enqueued":true}')]) as s:
            self.assertTrue(e.send_internal_review("ventas"))
            self.assertEqual(s.call_count,2)
            args=s.call_args[0][0]
            self.assertEqual(args[:4],["docker","exec","-u","node"])
            self.assertEqual(args[-1],"--json")
    def test_unsafe_job_rejected(self):
        class P:
            returncode=0
            stdout=json.dumps({"jobs":[{"id":e.ROLE_JOB_IDS["ventas"],
                 "enabled":True,"sessionTarget":"isolated",
                 "payload":{"kind":"agentTurn","toolsAllow":["exec","write"]},
                 "delivery":{"mode":"none"}}]})
        with patch.object(e.subprocess,"run",return_value=P()) as s:
            self.assertFalse(e.send_internal_review("ventas"))
            s.assert_called_once()
    def test_no_chat_api_calls_in_router(self):
        import inspect
        source=inspect.getsource(e)
        self.assertNotIn("Chatwoot::",source)
        self.assertNotIn("requests.post(",source)
        self.assertNotIn("docker restart",source)
    def test_trigger_role_once_and_dedupe(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prepare(root,*fixtures())
            with patch.object(e,"send_internal_review",return_value=True) as sent:
                first=e.run(root,dispatch=True)
                second=e.run(root,dispatch=True)
                self.assertEqual(first["dispatched_roles"],["ventas"])
                self.assertEqual(second["dispatched_roles"],[])
                sent.assert_called_once_with("ventas")
                self.assertEqual(first["public_messages_sent"],0)
                self.assertEqual(first["external_commercial_actions"],0)
            with sqlite3.connect(root/"events.sqlite3") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatch").fetchone()[0],1)

    def test_unsafe_specialist_cannot_send(self):
        self.assertFalse(e.send_internal_review("unknown"))
        self.assertFalse(e.send_internal_review(""))

    def test_json_is_roundtrippable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            prepare(root,*fixtures())
            e.run(root)
            self.assertEqual(json.loads((root/"EVENTS.json").read_text())["queued"],1)

if __name__=="__main__":
    unittest.main()
