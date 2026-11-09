#!/usr/bin/env python3
"""Autonomous offline sales QA and patch search; never deploy or contact clients."""
import argparse
from datetime import datetime,timezone
import difflib,fcntl,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
import build_sales_followup_candidate as builder
import sales_conversation_quality as dialogue
import sales_heldout_challenges as holdout
import sales_adversarial_quality as adversarial_cases
import conversion_training_lab as legacy
import inventory_training_lab as ruby
import sales_ai_challenges as adversarial
import sales_rotating_challenges as rotating
from quality_auditor import _atomic_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"quality"/"autonomous-sales"
LOCK=ROOT/"quality"/"autonomous-sales.lock"
REPORT=OUT/"latest.json"
SOURCE=builder.BOT
MAX_ITERATIONS=4
# These are reviewed deterministic alternative recipes, NOT arbitrary model code.
RECIPES=[
 ("reserve_synonyms",
  "reservarlo|reservarla|reservar|apartar|apartarlo|apartas|apartarme|separarlo|separar|guardan|guardar",
  "reservarlo|reservarla|reservar|reservas|reservame|apartar|apartarlo|apartas|apartarme|separarlo|separar|guardan|guardar|guardarme"),
 ("shipping_eta_synonyms",
  "en cuanto tiempo llega|cuando estaria|cuantos dias tardaria",
  "en cuanto tiempo llega|cuanto demora|cuando estaria|en que fecha llegaria|cuantos dias tardaria"),
 ("negotiation_synonyms",
  "si lo autorizan|si me lo bajas|entonces si autorizan",
  "si lo autorizan|si autorizan|si me lo bajas|si acepta el precio|entonces si autorizan"),
]
PROHIBITED=re.compile(
 r"\b(?:system|eval|exec|spawn|fork|require|load|IO|File|Process|Open3|"
 r"Kernel|ObjectSpace|Thread|Net::HTTP|FileUtils)\b|https?://|::|"
 r"(?i:chatwoot|waha|smtp|webhook|token|api_key|SOFTMOBILE_REPAIRS|send_message)"
)
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def initial():
 return {"schema_version":1,"at":stamp(),"environment":"OFFLINE_AUTONOMOUS_SALES",
  "scope":"sales_only","status":"blocked","source_pinned":False,"baseline":None,
  "reviewed_recipe_sha256":sha(builder.ADDITIONS),
  "winning_candidate":None,"evaluations":[],"candidate_staged":False,
  "candidate_integrated":False,"candidate_deployed":False,
  "deployment_authorized":False,"manual_review_required":True,
  "public_messages_sent":0,"ai_api_calls":0,"real_sales":0,
  "payments_initiated":0,"real_inventory_modified":False,
  "real_customer_data_loaded":False,"active_ruby_modified":False,
  "independent_production_qa_converged":False,
  "resumed_previous_candidate":False,"auto_corrected_ever":False,
  "ai_challenges_available":False,"ai_challenge_count":0,
  "ai_challenge_qa_passed":False,"challenge_source":"not_available",
  "challenge_count":0,"challenge_qa_passed":False}
def guard(original,candidate):
 if sha(original)!=builder.FROZEN_SHA:raise ValueError("source drift")
 anchor=builder.ANCHOR
 if original.count(anchor)!=1 or candidate.count(anchor)!=1:
  raise ValueError("missing trusted insertion anchor")
 a,b=original.split(anchor,1)
 if not candidate.startswith(a+anchor) or not candidate.endswith(b):
  raise ValueError("modified non-sales code")
 inserted=candidate[len(a+anchor):len(candidate)-len(b)]
 if not 100<len(inserted)<15000 or PROHIBITED.search(inserted):
  raise ValueError("unsafe scope")
 if (inserted.count("SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN")!=1 or
     inserted.count("SALES_ONLY_FOLLOWUPS_CANDIDATE_END")!=1):
  raise ValueError("unsafe candidate markers")
 for marker in ("PILOT_CONVERSATION_ID = 3","AUTO_REPLY_LIMIT = 1",
                "\nif ENV['SM_MODE']=='test'\n"):
  if marker not in candidate:raise ValueError("pilot marker removed")
 return True
def bounded_next(candidate,recipe):
 _,needle,replacement=recipe
 start=candidate.index("      # SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN")
 end=candidate.index("      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END")
 region=candidate[start:end]
 if region.count(needle)!=1:raise ValueError("recipe anchor drift")
 return candidate[:start]+region.replace(needle,replacement,1)+candidate[end:]
def verified_generated_challenges(now=None):
 """Load only recent six-turn fictional buyer fixtures. NO Groq calls here."""
 file=OUT/"ai-challenges.json"
 if not file.is_file():return []
 try:
  data=json.loads(file.read_text())
  at=datetime.fromisoformat(data["at"].replace("Z","+00:00"))
  now=now or datetime.now(timezone.utc)
  age=(now-at).total_seconds()
  if (not 0<=age<=172800 or data.get("schema_version")!=1 or
      data.get("mode")!="AI_FICTIONAL_SALES_CHALLENGES" or
      data.get("source")!="groq_synthetic_only" or
      data.get("real_customer_data_loaded") is not False or
      data.get("public_messages_sent")!=0 or
      data.get("code_generated") is not False or
      data.get("deployment_authorized") is not False):
   raise ValueError("untrusted or stale AI fixture")
  records=adversarial.validate({"examples":data["scenarios"]})
  tasks=[]
  for i,case in enumerate(records):
   tasks.append({
      "id":f"ai-holdout-{i:02d}","family":case["family"],
      "messages":["Busco iPhone 14 Pro Max de 256 GB negro",
                  case["prior"],case["followup"]],
      "destination":adversarial.fold(case["day_or_city"]),"expected":"not_found"})
  ruby.validate_scenarios([{k:x[k] for k in ("id","messages","expected")}
                             for x in tasks])
  return tasks
 except (OSError,ValueError,TypeError,KeyError,AttributeError):
  raise ValueError("AI fixture verification blocked")

def check_generated(source,tasks):
 if not tasks:return {"available":False,"passed":0,"tested":0},True
 checked=[]
 for block in (tasks[:3],tasks[3:]):
  traces=ruby.parse_with_real_ruby([
   {"id":row["id"],"messages":row["messages"],"expected":"not_found"}
   for row in block],source=source)
  if len(traces)!=len(block):
   raise ValueError("missing generated challenge trace")
  checked.extend(holdout.score(task,trace) for task,trace in zip(block,traces))
 report={"available":True,"passed":sum(x["passed"] for x in checked),
         "tested":len(checked),"failed_ids":[x["id"] for x in checked if not x["passed"]]}
 return report,report["passed"]==len(checked)

def choose_reviewed_recipe(result,challenges,available):
 """Select ONLY a pre-reviewed transformation from observed failure family."""
 known={x[0] for x in available}
 failures=set()
 for grouping in ("dialogue_by_family","holdout_by_family"):
  for family,count in (result.get(grouping) or {}).items():
   if (type(count.get("tested")) is int and
       type(count.get("passed")) is int and
       count["passed"]<count["tested"]):
    failures.add(family)
 ids=set((result.get("generated_challenges") or {}).get("failed_ids",[]))
 failures.update(row["family"] for row in challenges if row["id"] in ids)
 edges=(result.get("adversarial_cases") or {}).get("failed_ids",[])
 if isinstance(edges,list):
  for item in edges:
   if not isinstance(item,str) or not re.fullmatch(r"edges-\d{2}",item):
    continue
   index=int(item.split("-")[-1])
   if index>=len(adversarial_cases.ROWS):
    continue
   topic=adversarial_cases.ROWS[index][0]
   if topic.startswith("reserve_"):failures.add("reservation")
   if topic.startswith("shipment_"):failures.add("shipping")
   if topic=="discount":failures.add("negotiation")
 choices={"reservation":"reserve_synonyms",
          "shipping":"shipping_eta_synonyms",
          "negotiation":"negotiation_synonyms"}
 for family in ("reservation","shipping","negotiation"):
  recipe=choices[family]
  if family in failures and recipe in known:
   return next(row for row in available if row[0]==recipe)
 return available[0] if available else None

def check_ruby(original,candidate,generated=None):
 guard(original,candidate)
 a=dialogue.run(source=candidate)
 h=holdout.run(source=candidate)
 if (a.get("source_sha256")!=sha(candidate) or h.get("source_sha256")!=sha(candidate) or
     a.get("scenarios")!=72 or h.get("scenarios")!=18 or
     a.get("public_messages_sent")!=0 or h.get("public_messages_sent")!=0 or
     a.get("api_calls")!=0 or h.get("api_calls")!=0 or
     a.get("real_sales")!=0 or h.get("real_sales")!=0 or
     a.get("production_modified") is not False or
     h.get("production_modified") is not False):
  raise ValueError("untrusted QA source")
 result={"dialogue_passed":a["passed"],"dialogue_total":72,
         "holdout_passed":h["passed"],"holdout_total":18,
         "dialogue_by_family":a["by_family"],
         "holdout_by_family":h["by_family"],
         "holdout_failed_ids":h["failed_ids"]}
 challenge,challenge_ok=check_generated(candidate,generated or [])
 result["generated_challenges"]=challenge
 edge=adversarial_cases.run(source=candidate)
 if (edge.get("environment")!="INDEPENDENT_FICTIONAL_SALES_EDGE_CASES" or
     edge.get("source_sha256")!=sha(candidate) or
     edge.get("scenarios")!=11 or edge.get("public_messages_sent")!=0 or
     edge.get("api_calls")!=0 or edge.get("real_sales")!=0 or
     edge.get("production_changed") is not False):
  raise ValueError("invalid adversarial QA")
 result["adversarial_cases"]={"passed":edge["passed"],
       "tested":11,"failed_ids":edge["failed_ids"]}
 return result,(result["dialogue_passed"]==72 and
                result["holdout_passed"]==18 and
                result["adversarial_cases"]["passed"]==11 and challenge_ok)
def legacy_regression(candidate):
 d,_=legacy.run(source=candidate,persist=False)
 if (d.get("scenarios")!=72 or d.get("passed")!=72 or
     d.get("failed")!=0 or d.get("unverified_promises")!=0 or
     d.get("public_messages_sent")!=0 or d.get("real_orders")!=0 or
     d.get("real_inventory_modified") is not False):
  raise ValueError("legacy checkout/safety regression")
 return 72
def unit_regression():
 r=subprocess.run(["/usr/bin/python3","-m","unittest","-q",
      "test_sales_conversation_quality","test_conversion_training_lab",
      "test_sales_adversarial_quality",
      "test_sales_ai_agent","test_reference_inventory",
      "test_reference_commerce_firewall"],
      cwd=ROOT,text=True,capture_output=True,check=False,timeout=170,
      env={"PATH":"/usr/local/bin:/usr/bin:/bin","HOME":"/tmp",
           "PYTHONDONTWRITEBYTECODE":"1"})
 n=re.search(r"Ran (\d+) tests? in",r.stderr)
 if r.returncode or not n or int(n.group(1))<68:
  raise ValueError("independent unit regression failure")
 return int(n.group(1))
def private_write(path,content):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd,tmp=tempfile.mkstemp(prefix=".sales-",dir=path.parent)
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,"w",encoding="utf8") as f:
   f.write(content);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def stage(original,candidate):
 diff="".join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),
       fromfile="a/sales-bot-v2.rb",tofile="b/sales-bot-v2.rb"))
 if not 40<len(diff)<16500:raise ValueError("oversized patch")
 digest=sha(candidate)
 p=OUT/"candidates"/("candidate-"+digest[:16])
 private_write(Path(str(p)+".rb"),candidate)
 private_write(Path(str(p)+".patch"),diff)
 if sha(Path(str(p)+".rb").read_text())!=digest:
  raise ValueError("staged SHA mismatch")
 return {"sha256":digest,"candidate_file":str(p)+".rb",
         "patch_file":str(p)+".patch","auto_deploy":False}
def previous_reviewed_candidate(original):
 """Resume only our own SHA-checked prior review artifact, not production."""
 if not REPORT.is_file():
  return None
 try:
  old=json.loads(REPORT.read_text())
  if (old.get("status")!="qa_passed_review_required" or
      old.get("source_sha256")!=sha(original) or
      old.get("reviewed_recipe_sha256")!=sha(builder.ADDITIONS) or
      old.get("candidate_deployed") is not False or
      old.get("public_messages_sent")!=0):
   return None
  artifact=old.get("winning_candidate") or {}
  candidate_path=Path(artifact["candidate_file"])
  patch_path=Path(artifact["patch_file"])
  if (candidate_path.is_symlink() or patch_path.is_symlink() or
      candidate_path.parent!=OUT/"candidates" or
      patch_path.parent!=OUT/"candidates" or
      not candidate_path.is_file() or not patch_path.is_file() or
      artifact.get("auto_deploy") is not False):
   raise ValueError("previous artifact location untrusted")
  candidate=candidate_path.read_text()
  if sha(candidate)!=artifact["sha256"]:
   raise ValueError("previous candidate SHA mismatch")
  guard(original,candidate)
  return candidate
 except (OSError,TypeError,KeyError,ValueError,AttributeError) as exc:
  raise ValueError("previous candidate not trusted") from exc

def one_cycle():
 state=initial()
 original=SOURCE.read_text()
 state["source_sha256"]=sha(original)
 if SOURCE.is_symlink() or sha(original)!=builder.FROZEN_SHA:
  state["status"]="source_drift_blocked";return state
 state["source_pinned"]=True
 # Historical recipe baseline must be scored against its pinned archived
 # Ruby, never implicitly against the newly promoted active seller.
 baseline=dialogue.run(source=original)
 if (baseline.get("candidate") is not True or
     baseline.get("source_sha256")!=sha(original) or
     baseline.get("scenarios")!=72 or
     baseline.get("public_messages_sent")!=0):
  state["status"]="untrusted_baseline";return state
 state["baseline"]={"passed":baseline["passed"],"tested":72}
 try:generated=verified_generated_challenges()
 except ValueError:
  state["status"]="ai_challenges_invalid_blocked"
  return state
 state["ai_challenges_available"]=bool(generated)
 state["ai_challenge_count"]=len(generated)
 if not generated:
  generated=rotating.tasks()
  state["challenge_source"]="reviewed_rotating_local_bank"
 else:
  state["challenge_source"]="verified_ai_fictional_bank"
 state["challenge_count"]=len(generated)
 if generated:
  original_challenge,_=check_generated(original,generated)
  state["baseline_challenge"]=original_challenge
 previous=previous_reviewed_candidate(original)
 state["resumed_previous_candidate"]=previous is not None
 candidate=previous if previous is not None else builder.make(original)
 start=candidate.index("      # SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN")
 end=candidate.index("      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END")
 region=candidate[start:end]
 remaining=[r for r in RECIPES if r[1] in region and r[2] not in region]
 for i in range(MAX_ITERATIONS):
  record={"attempt":i+1,"candidate_sha256":sha(candidate),
          "status":"rejected"}
  try:
   detail,passed=check_ruby(original,candidate,generated)
   if generated:
    success=detail["generated_challenges"]["passed"]==len(generated)
    state["challenge_qa_passed"]=success
    if state["ai_challenges_available"]:
     state["ai_challenge_qa_passed"]=success
   record.update(detail)
   if passed:
    record["legacy_checkout_passed"]=legacy_regression(candidate)
    record["unit_tests_passed"]=unit_regression()
    record["reference_only_agent_firewall_verified"]=True
    if sha(SOURCE.read_text())!=sha(original):
     raise ValueError("source changed while testing")
    state["winning_candidate"]=stage(original,candidate)
    state["candidate_staged"]=True
    record["status"]="qa_passed_review_required"
    state["status"]="qa_passed_review_required"
    state["evaluations"].append(record)
    break
   record["status"]="synthetic_replies_failed"
  except (RuntimeError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired) as e:
   record["status"]="rejected_"+type(e).__name__
  state["evaluations"].append(record)
  if record["status"].startswith("rejected_"):
   state["status"]="qa_error_blocked"
   break
  chosen=choose_reviewed_recipe(record,generated,remaining)
  if chosen is None:
   state["status"]="no_more_safe_recipes"
   break
  remaining.remove(chosen)
  try:candidate=bounded_next(candidate,chosen)
  except ValueError:
   state["status"]="recipe_drift_blocked";break
 return state
def run():
 OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
 with LOCK.open("a+",encoding="utf8") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  state=initial()
  try:state=one_cycle()
  except (RuntimeError,OSError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired):
   state["status"]="blocked_unexpected_source_or_runner"
  state["completed_at"]=stamp()
  try:
   previous=json.loads(REPORT.read_text())
  except (OSError,ValueError):
   previous={}
  state["auto_corrected_ever"]=(
    len(state["evaluations"])>1 or
    (previous.get("auto_corrected_ever") is True) or
    len(previous.get("evaluations") or [])>1)
  _atomic_json(REPORT,state)
  try:
   history=json.loads((OUT/"history.json").read_text())
   if not isinstance(history,list):history=[]
  except (OSError,ValueError):
   history=[]
  event={"at":state["completed_at"],"status":state["status"],
         "attempts":len(state["evaluations"]),
         "resumed":state.get("resumed_previous_candidate",False),
         "challenge_source":state.get("challenge_source"),
         "challenge_count":state.get("challenge_count",0),
         "adversarial_passed":(
           (state["evaluations"][-1].get("adversarial_cases") or {}).get("passed")
           if state["evaluations"] else None),
         "candidate_sha256":(state.get("winning_candidate") or {}).get("sha256"),
         "public_messages_sent":0,"candidate_deployed":False}
  _atomic_json(OUT/"history.json",(history+[event])[-120:])
  private_write(OUT/"latest.md",
   "# SoftMobile: búsqueda automática de mejora de ventas\n\n"+
   "Estado: "+state["status"]+"\n"+
   "Ensayos: "+str(len(state["evaluations"]))+"\n"+
   "Candidato interno: "+str(state["candidate_staged"])+
   ". No se han enviado mensajes ni desplegado código.\n")
  return state
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--run",action="store_true")
 ap.add_argument("--status",action="store_true")
 a=ap.parse_args()
 if a.status:
  print(json.dumps(json.loads(REPORT.read_text()) if REPORT.exists()
        else {"status":"not_started"},ensure_ascii=False))
  return 0
 if not a.run:ap.error("use --run or --status")
 try:result=run()
 except BlockingIOError:
  print(json.dumps({"status":"skipped_busy"}));return 0
 print(json.dumps({"status":result["status"],
       "staged":result["candidate_staged"],
       "attempts":len(result["evaluations"]),
       "public_messages_sent":0,"deployed":False}))
 return 0 if result["status"]=="qa_passed_review_required" else 2
if __name__=="__main__":raise SystemExit(main())