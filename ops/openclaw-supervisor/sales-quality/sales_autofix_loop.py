#!/usr/bin/env python3
"""Autonomous offline sales QA and patch search; never deploy or contact clients."""
import argparse
from datetime import datetime,timezone
import difflib,fcntl,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
import build_sales_followup_candidate as builder
import sales_conversation_quality as dialogue
import sales_heldout_challenges as holdout
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
MAX_ITERATIONS=3
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
  "winning_candidate":None,"evaluations":[],"candidate_staged":False,
  "candidate_integrated":False,"candidate_deployed":False,
  "deployment_authorized":False,"manual_review_required":True,
  "public_messages_sent":0,"ai_api_calls":0,"real_sales":0,
  "payments_initiated":0,"real_inventory_modified":False,
  "real_customer_data_loaded":False,"active_ruby_modified":False,
  "independent_production_qa_converged":False,
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
 if not 100<len(inserted)<7500 or PROHIBITED.search(inserted):
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
 return result,(result["dialogue_passed"]==72 and
                result["holdout_passed"]==18 and challenge_ok)
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
      "test_sales_conversation_quality","test_conversion_training_lab"],
      cwd=ROOT,text=True,capture_output=True,check=False,timeout=170,
      env={"PATH":"/usr/local/bin:/usr/bin:/bin","HOME":"/tmp",
           "PYTHONDONTWRITEBYTECODE":"1"})
 n=re.search(r"Ran (\d+) tests? in",r.stderr)
 if r.returncode or not n or int(n.group(1))<21:
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
def one_cycle():
 state=initial()
 original=SOURCE.read_text()
 state["source_sha256"]=sha(original)
 if SOURCE.is_symlink() or sha(original)!=builder.FROZEN_SHA:
  state["status"]="source_drift_blocked";return state
 state["source_pinned"]=True
 baseline=dialogue.run()
 if (baseline.get("candidate") is not False or
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
 candidate=builder.make(original)
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
  if i<len(RECIPES):
   try:candidate=bounded_next(candidate,RECIPES[i])
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
  _atomic_json(REPORT,state)
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
