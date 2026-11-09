#!/usr/bin/env python3
"""Eleven independent sales dialogues to catch missed colloquial transitions.

Uses real Ruby replies in disposable networkless Docker. Does not execute
orders, edit stock, invoke AI or send messages. Entirely fictional.
"""
import json,re
from hashlib import sha256
from datetime import datetime,timezone
from pathlib import Path
from inventory_training_lab import parse_with_real_ruby
from sales_conversation_quality import fold,CITY_REPEAT

BASE="Busco iPhone 14 Pro Max de 256 GB negro"
ROWS=[
 ("discount","Si me lo dejás más barato, lo compro",
  [BASE,"¿Hay descuento?","Si me lo dejás más barato, lo compro"]),
 ("cash_checkout","Si el precio me sirve, compro ahora",
  ["Busco Samsung S24 Ultra 256 GB azul","Necesito precio por efectivo","Si el precio me sirve, compro ahora"]),
 ("reserve_friday","viernes",
  [BASE,"¿Me lo guardás?","¿Podés apartármelo para el viernes?"]),
 ("reserve_wednesday","miercoles",
  [BASE,"Me interesa apartarlo","Apartámelo el miércoles si está disponible"]),
 ("shipment_days","choloma",
  [BASE,"Lo quiero para envío a Choloma","¿Cuántos días se tarda?"]),
 ("shipment_price","choloma",
  [BASE,"Soy de Choloma y lo necesito con envío","¿Cuánto cobrarían por mandármelo?"]),
 ("shipment_ETA_city","san pedro sula",
  ["Busco Samsung S24 Ultra 256 GB azul","Vivo en San Pedro Sula, necesito envío","¿Cuánto demora llegar a mi casa?"]),
 ("cancel_interest","no sigo",
  [BASE,"¿Puedo reservarlo para mañana?","Mejor ya no quiero, cancelo"]),
 ("payment_unverified","comprobar",
  [BASE,"Quiero pagar por transferencia","Ya pagué, confirma por favor"]),
 ("finance_not_approved","aprobacion",
  [BASE,"¿Puedo financiar con BAC?","¿Me confirmás que me aprobaron crédito?"]),
 ("variant_change","128gb",
  [BASE,"¿Lo tenés?","Mejor el de 128 GB en azul, ¿lo tenés?"]),
]

FALSE_CLAIMS=re.compile(
 r"\b(?:ya esta reservado|ya lo apartamos|pago confirmado|"
 r"credito aprobado|aprobamos tu credito|descuento aprobado|"
 r"entrega garantizada|ya lo enviamos|ya lo cancelamos)\b")

def records():
 return [{"id":f"edges-{i:02d}","messages":messages,"expected":"not_found"}
         for i,(_,_,messages) in enumerate(ROWS)]

def score(row,trace):
 idx=int(row["id"].split("-")[-1])
 name,target,_=ROWS[idx]
 if trace.get("id")!=row["id"] or len(trace.get("steps",[]))!=3:
  raise ValueError("incomplete Ruby dialogue")
 final=fold(trace["steps"][-1]["baseline"])
 passed=(len(final)>=15 and len(final)<=240 and not FALSE_CLAIMS.search(final))
 if name=="discount":
  passed &= ("precio" in final or "rebaja" in final) and (
    "revis" in final or "confirm" in final or "pendiente" in final)
 elif name=="cash_checkout":
  passed &= ("precio" in final and ("confirm" in final or "verific" in final))
 elif name.startswith("reserve_"):
  passed &= (target in final and re.search(r"reserv|apart",final) is not None
             and re.search(r"no esta reservad|no hay reserva|todavia no|verific|antes de",final) is not None)
 elif name.startswith("shipment_"):
  passed &= target in final and re.search(r"envio|transport|tarifa|plazo|entrega",final) is not None
  passed &= CITY_REPEAT.search(final) is None
  if name=="shipment_price":passed &= "costo" in final or "tarifa" in final
 elif name=="cancel_interest":
  passed &= "no sigo" in final and "compra" in final
 elif name=="payment_unverified":
  passed &= "pago" in final and "comprobar" in final
 elif name=="finance_not_approved":
  passed &= ("aprob" in final and "banco" in final and "no" in final)
 elif name=="variant_change":
  passed &= "128gb" in final and "azul" in final
 return {"id":row["id"],"topic":name,"passed":bool(passed)}

def run(source=None):
 if source is not None and not isinstance(source,str):raise ValueError("source")
 cases=records()
 result=parse_with_real_ruby(cases,source=source)
 if len(result)!=len(cases):raise ValueError("missing Ruby cases")
 marked=[score(r,o) for r,o in zip(cases,result)]
 return {"at":datetime.now(timezone.utc).isoformat(),
   "environment":"INDEPENDENT_FICTIONAL_SALES_EDGE_CASES",
   "source_sha256":sha256(source.encode()).hexdigest() if source is not None
      else sha256(Path("/opt/softmobile-waha-test/sales-bot-v2.rb").read_bytes()).hexdigest(),
   "candidate":source is not None,
   "scenarios":len(marked),"passed":sum(x["passed"] for x in marked),
   "failed_ids":[x["id"] for x in marked if not x["passed"]],
   "by_topic":{x["topic"]:x["passed"] for x in marked},
   "customer_messages_sent":0,"public_messages_sent":0,"api_calls":0,
   "real_sales":0,"real_stock_changed":False,"production_changed":False}
if __name__=="__main__":
 import sys
 src=Path(sys.argv[1]).read_text() if len(sys.argv)>1 else None
 print(json.dumps(run(src),ensure_ascii=False))
