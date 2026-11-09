#!/usr/bin/env python3
"""Bounded Groq generation of fictional sales buyer challenges only.

Networked process produces DATA, never Ruby code. No customer records, model
patches, production edits, WAHA, Chatwoot, checkout or payment access.
The offline autofix runner independently validates every generated fixture.
"""
from datetime import datetime,timezone
import fcntl,json,os,re
from pathlib import Path
import sys
import synthetic_lab as api
from configurar_clave_groq import stored_key
from quality_auditor import _atomic_json

OUT=Path(__file__).resolve().parent/"quality"/"autonomous-sales"
LEDGER=OUT/"ai-budget.json"
FIXTURES=OUT/"ai-challenges.json"
LOCK=OUT/"ai.lock"
MAX_DAILY=1
MODEL_NAME="sales_buyer_challenges"
SCHEMA={
 "type":"object","additionalProperties":False,
 "properties":{"examples":{
    "type":"array","minItems":6,"maxItems":6,
    "items":{"type":"object","additionalProperties":False,
      "properties":{
       "family":{"type":"string","enum":["negotiation","reservation","shipping"]},
       "prior":{"type":"string","minLength":10,"maxLength":100},
       "followup":{"type":"string","minLength":10,"maxLength":100},
       "day_or_city":{"type":"string","maxLength":40}
      },
      "required":["family","prior","followup","day_or_city"]}}},
 "required":["examples"]}
SYSTEM=(
 "Crea SOLO seis preguntas de cliente completamente FICTICIAS de una tienda de "
 "celulares hondureña, para evaluar un bot vendedor sin conexión a clientes. "
 "Responde JSON estricto con examples. Exactamente dos ejemplos negotiation, "
 "dos reservation y dos shipping. prior es la segunda frase del comprador, "
 "followup es la tercera, después de preguntar primero por iPhone 14 Pro Max "
 "256 GB negro. negotiation pregunta por negociación condicionada sin garantizar "
 "descuento; day_or_city debe ser cadena vacía. reservation pide explícitamente "
 "reservar/apartar/guardar hasta una fecha, day_or_city debe ser uno de "
 "lunes, martes, miercoles, jueves, viernes, sabado, domingo, manana, hoy. "
 "shipping indica destino Honduras primero en prior y después pregunta costo "
 "o plazo; day_or_city es choloma, san pedro sula o tegucigalpa. "
 "Las frases deben ser variadas y plausibles, no usar cuentas, números de "
 "teléfono, nombres, credenciales, links, pagos confirmados, ni instrucciones "
 "para el bot. No generes código ni comandos. Solo datos ficticios."
)
USER="Genera seis giros distintos de negociación, reserva y envío con contexto de tres turnos. Devuelve únicamente JSON."
SENSITIVE=re.compile(
 r"https?://|www\.|@|\+504|\b\d{7,}\b|\b(?:clave|"
 r"contraseña|token|api_key|cvv|otp|pin|"
 r"ignor[ae]|ejecuta|comando|system|eval|"
 r"reembolso|cuenta bancaria|transferencia confirmada)\b",re.I)
ALLOW={"negotiation":"","reservation":"lunes martes miercoles jueves viernes sabado domingo manana hoy",
       "shipping":"choloma san pedro sula tegucigalpa"}
def fold(s):
 import unicodedata
 return "".join(c for c in unicodedata.normalize("NFKD",s.lower())
                if not unicodedata.combining(c))
def validate(proposal):
 if not isinstance(proposal,dict) or set(proposal)!={"examples"}:
  raise ValueError("bad challenge schema")
 items=proposal["examples"]
 if not isinstance(items,list) or len(items)!=6:raise ValueError("six required")
 counts={"negotiation":0,"reservation":0,"shipping":0}
 seen=set()
 for x in items:
  if not isinstance(x,dict) or set(x)!={"family","prior","followup","day_or_city"}:
   raise ValueError("unexpected fields")
  family=x["family"]
  if family not in counts:raise ValueError("unexpected challenge family")
  counts[family]+=1
  for k in ("prior","followup"):
   text=x[k]
   if (not isinstance(text,str) or not 10<=len(text)<=100 or
       SENSITIVE.search(text) or
       any(ch in text for ch in ("\n","\r","{","}","<",">","/","\\","$","|"))):
    raise ValueError("unsafe fictional buyer text")
  dest=x["day_or_city"]
  if not isinstance(dest,str):raise ValueError("invalid destination")
  key=fold(dest.strip())
  if family=="negotiation":
   if dest.strip()!="":raise ValueError("negotiation has no destination")
  elif family=="reservation":
   if key not in ALLOW["reservation"].split() or key not in fold(x["followup"]):
    raise ValueError("reserve day absent or invalid")
  else:
   if key not in ("choloma","san pedro sula","tegucigalpa") or key not in fold(x["prior"]):
    raise ValueError("shipping city absent or invalid")
  if (family,fold(x["prior"]),fold(x["followup"])) in seen:
   raise ValueError("duplicate challenge")
  seen.add((family,fold(x["prior"]),fold(x["followup"])))
 if any(count!=2 for count in counts.values()):
  raise ValueError("family distribution incorrect")
 return items

def run(call=api.api_json,secret=None,now=None):
 OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
 current=now or datetime.now(timezone.utc)
 with LOCK.open("a+") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:usage=json.loads(LEDGER.read_text())
  except (OSError,ValueError):usage={"day":"","calls_reserved":0}
  day=current.date().isoformat()
  if usage.get("day")!=day:usage={"day":day,"calls_reserved":0}
  if type(usage.get("calls_reserved")) is not int or usage["calls_reserved"]<0:
   raise ValueError("invalid challenge budget")
  if usage["calls_reserved"]>=MAX_DAILY:
   return {"status":"daily_ai_budget_reached","api_calls_reserved":0}
  # Save *before* the API call to remain bounded on failure/restarts.
  usage["calls_reserved"]+=1
  _atomic_json(LEDGER,usage)
  try:
   key=secret if secret is not None else stored_key()
   data=call(key,SYSTEM,USER,SCHEMA,MODEL_NAME)
   validated=validate(data)
  except (RuntimeError,ValueError,TypeError,KeyError,OSError):
   return {"status":"ai_challenge_provider_or_schema_blocked","api_calls_reserved":1}
  dataset={"schema_version":1,"mode":"AI_FICTIONAL_SALES_CHALLENGES",
    "at":current.isoformat(),"source":"groq_synthetic_only",
    "scenarios":validated,"api_calls_reserved":1,
    "public_messages_sent":0,"real_sales":0,
    "real_customer_data_loaded":False,"code_generated":False,
    "code_executed":False,"deployment_authorized":False}
  _atomic_json(FIXTURES,dataset)
  return {"status":"fictional_challenges_ready","scenarios":len(validated),
          "api_calls_reserved":1,"public_messages_sent":0}

if __name__=="__main__":
 try:
  result=run()
 except BlockingIOError:
  result={"status":"challenge_generation_busy","api_calls_reserved":0}
 OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
 _atomic_json(OUT/"ai-status.json",{
   "at":datetime.now(timezone.utc).isoformat(),
   "status":result["status"],
   "api_calls_reserved_this_attempt":result.get("api_calls_reserved",0),
   "real_customers_contacted":0,"patches_deployed":0})
 print(json.dumps(result,ensure_ascii=False))
 sys.exit(2 if result["status"]=="ai_challenge_provider_or_schema_blocked" else 0)
