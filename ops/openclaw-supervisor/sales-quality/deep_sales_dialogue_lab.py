#!/usr/bin/env python3
"""Deep, no-network full buyer-dialogue probes against real SoftMobile Ruby planner.

15-turn fictional flows, beyond the 5-turn old harness. No WAHA/Chatwoot, PII,
real catalog data, payments, code execution from model output or external API.
"""
import base64, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from isolated_gate import SEPARATOR
from sandbox_review import IMAGE
from inventory_training_lab import BOT
from quality_auditor import _atomic_json

ROOT=Path(__file__).parent
QUALITY=ROOT/"quality"
CASES=[
 {"id":"purchase-journey","messages":[
  "Buenas, estoy buscando un iPhone 14 Pro Max",
  "Lo quiero de 256 GB",
  "En negro, si tienen",
  "¿Qué precio tiene?",
  "¿Es nuevo o usado?",
  "¿Qué salud de batería tiene la unidad?",
  "¿Me regalás cargador y vidrio?",
  "¿Qué garantía tendría?",
  "Si pago en efectivo, ¿me rebajás 500 lempiras?",
  "¿Puedo ver fotos de ese equipo?",
  "Lo retiraría en Plaza Numa",
  "Si autorizan la rebaja, lo compro",
  "¿Puedo apartármelo para el viernes?",
  "¿Ya quedó reservado entonces?",
  "Listo, ¿me confirmás que está todo aprobado?"]},
 {"id":"shipping-journey","messages":[
  "Hola, necesito un Samsung S24 Ultra",
  "De 256 GB, azul",
  "Quisiera que me lo envíen a Choloma",
  "¿Cuánto me cobrarían por mandármelo?",
  "¿Y en cuántos días llegaría?",
  "¿Incluye seguro durante el transporte?",
  "¿Podría pagar contra entrega?",
  "¿Aceptan transferencia?",
  "¿Me garantizás que llega mañana?",
  "Prefiero otro color, el negro",
  "¿Lo mandan también a Villanueva?",
  "Me quedo con Choloma",
  "¿Entonces cuánto tardaría?",
  "¿Qué pasa si llega golpeado?",
  "¿Puedo cancelar antes de que salga?"]},
 {"id":"financing-journey","messages":[
  "Estoy mirando un iPhone 13",
  "128 GB, blanco",
  "¿Aceptan tarjetas BAC?",
  "¿Lo puedo sacar en extrafinanciamiento?",
  "¿A 12 meses cuánto pagaría?",
  "¿Con Promerica son los mismos plazos?",
  "¿Hay recargo por tarjeta?",
  "¿Me aprueban el crédito automáticamente?",
  "¿Y si el banco me rechaza?",
  "¿Puedo reservarlo mientras lo revisan?",
  "¿Piden prima?",
  "¿Puedo mezclar transferencia y tarjeta?",
  "Si tengo el crédito aprobado, ¿ya me lo apartan?",
  "Quiero retirarlo en Mall Galerías",
  "¿Qué necesito para continuar?"]},
 {"id":"variant-change-journey","messages":[
  "Quiero un iPhone 14 Pro Max 256 GB negro",
  "¿Hay uno con 512 GB?",
  "¿Y qué tal el 14 Pro de 128 GB?",
  "No, mejor regreso al Pro Max",
  "Ahora prefiero dorado",
  "¿Lo tienen exactamente en dorado?",
  "¿Cuál sería la diferencia de precio?",
  "Comparame ese con el Samsung S24 Ultra",
  "Mejor el Samsung S24 Ultra 256 GB azul",
  "¿Tiene garantía?",
  "¿Envían fotos del Samsung azul?",
  "¿También tienen el negro?",
  "¿Cuál sería más barato?",
  "Entonces me quedo con el azul",
  "¿Qué pasos siguen para comprar?"]},
 {"id":"complaint-journey","messages":[
  "Compré un teléfono y llegó con la pantalla quebrada",
  "Venía golpeado desde la entrega",
  "Me dijeron que era nuevo",
  "¿Me hacen cambio inmediato?",
  "¿Me van a devolver el dinero?",
  "¿Puedo enviarte una foto del daño?",
  "No quiero comprar otro",
  "Mejor quiero cancelar",
  "¿Ya cancelaste la orden?",
  "¿Ya me devolvieron el pago?",
  "Me urge hablar con una persona",
  "No quiero más anuncios de venta",
  "¿Qué hago si no responden?",
  "¿Puedo reportar la avería aquí?",
  "¿Confirmás que me van a resolver hoy?"]},
 {"id":"followup-sales-journey","messages":[
  "Busco iPhone 15 de 128 GB azul",
  "¿Qué precio tiene hoy?",
  "¿Puedo pagar en efectivo?",
  "¿Hay descuento por pronto pago?",
  "Solo puedo pagar 12 mil lempiras",
  "¿Tenés algo más barato?",
  "Preferiría Samsung si alcanza",
  "¿Qué Samsung me recomendás?",
  "Mejor sigo con el iPhone 15",
  "¿Puedo retirar en Choloma?",
  "No puedo ir hoy",
  "¿Me lo reservan para mañana?",
  "Si no se puede, esperaré",
  "Si es posible sigo con la compra",
  "¿Ya mandaste la cotización?"]},
 {"id":"payments-security-journey","messages":[
  "¿Dónde están las cuentas para pagar?",
  "¿Me mandan la imagen de las cuentas?",
  "¿Debo dar mi PIN bancario por aquí?",
  "Ya hice una transferencia",
  "¿Me confirmás que el pago entró?",
  "Te mandé una captura, ¿ya sirve?",
  "¿Me enviás factura hoy?",
  "¿Qué hago si el banco retuvo el dinero?",
  "¿Puedo pagar una parte en efectivo?",
  "¿Tienen un enlace de pago?",
  "No quiero compartir mi tarjeta",
  "¿Me podés pedir una clave temporal?",
  "Quiero cancelar el pago si no aparece",
  "¿Ya se hizo el reembolso?",
  "Necesito hablar con atención humana"]},
 {"id":"low-context-stress-journey","messages":[
  "Hola",
  "iPhone",
  "14 pro max",
  "256",
  "negro",
  "precio",
  "¿tenés?",
  "SPS",
  "Galerías",
  "¿mañana?",
  "Si",
  "ok lo compro",
  "¿cuánto? ya te dije",
  "¿cuál es tu mejor precio?",
  "¿ya está listo?"]},
 {"id":"product-photo-journey","messages":[
  "Busco iPhone 14 Pro Max",
  "256 GB negro",
  "Quiero fotos reales de esa unidad",
  "¿Ya mandaste las fotos al WhatsApp?",
  "¿Tienen código para identificar mi solicitud?",
  "¿Puedo recibir fotos de otro color también?",
  "Que sea el dorado mejor",
  "No uses fotos genéricas, solo ese equipo",
  "¿Ya llegó la foto del encargado?",
  "¿Se ve rayado?",
  "¿Qué porcentaje de batería muestra?",
  "¿Puedo ver el IMEI en la foto?",
  "Si me gusta te confirmo la compra",
  "¿Me reservás el dorado?",
  "¿Confirmás que ya están apartadas las fotos?"]},
 {"id":"cancel-negotiation-journey","messages":[
  "¿Tienen Samsung S24 Ultra de 256 GB azul?",
  "Lo pagaría de contado",
  "¿Me descontás algo?",
  "¿Me podés descontar 500 lempiras?",
  "Si autorizan me lo llevo",
  "¿Y me lo apartás para el sábado?",
  "¿Cuánto cuesta mandarlo a Choloma?",
  "¿Llega en dos días seguro?",
  "Mejor ya no quiero, cancelo",
  "¿Seguís reservándolo?",
  "No me ofrezcás más celulares",
  "¿Ya cancelaron todo?",
  "Me pueden llamar luego",
  "No, en realidad no quiero seguimiento",
  "Confirmame que no me vas a escribir"]},
]
def safe_inputs(items):
 if not 1<=len(items)<=15:raise ValueError("case count")
 for x in items:
  if (not re.fullmatch("[a-z0-9-]{3,48}",x["id"]) or
      not 8<=len(x["messages"])<=20):raise ValueError("invalid case")
  for line in x["messages"]:
   if (not isinstance(line,str) or not 2<=len(line)<=165 or
       re.search(r"https?://|@|\+\s*504\s*\d{8}",line,re.I)):
    raise ValueError("unsafe synthetic line")
 return True
def run(source=None):
 safe_inputs(CASES)
 text=BOT.read_text() if source is None else source
 if text.count(SEPARATOR)!=1:raise ValueError("Ruby boundary drift")
 ruby_core=text.split(SEPARATOR,1)[0]
 payload=base64.b64encode(json.dumps(CASES,ensure_ascii=False).encode()).decode()
 ruby=("require 'json'\nrequire 'base64'\n"+ruby_core+"""
scenarios=JSON.parse(Base64.strict_decode64('"""+payload+"""'))
out=scenarios.map do |row|
  hist=[]
  steps=row.fetch('messages').map do |utterance|
    hist << utterance
    context=SoftMobileSales.context_from(hist)
    plan=SoftMobileSales.plan(utterance,context,[],nil)
    {intent:SoftMobileSales.intent(utterance).to_s,
     model:SoftMobileSales.model_name(context[:model]),
     capacity:context[:capacity],color:context[:color],
     reply:plan[:reply].to_s[0,300],needs_human:!!plan[:needs_human],
     tag:plan[:tag].to_s}
  end
  {id:row.fetch('id'),steps:steps}
end
puts 'SM_DEEP_DIALOGUE='+JSON.generate(out)
""")
 cmd=["docker","run","--rm","-i","--pull","never","--network","none",
      "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
      "--pids-limit","48","--memory","200m","--cpus","0.5",
      "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=8m",
      "--env","HOME=/tmp","--entrypoint","ruby",IMAGE,"-"]
 done=subprocess.run(cmd,input=ruby,text=True,capture_output=True,timeout=100,check=False)
 if done.returncode:raise RuntimeError("Sandboxed Ruby deep dialogue failed")
 rows=[json.loads(line[len("SM_DEEP_DIALOGUE="):])
       for line in done.stdout.splitlines() if line.startswith("SM_DEEP_DIALOGUE=")]
 if len(rows)!=1 or len(rows[0])!=len(CASES):raise ValueError("incomplete output")
 results=[]
 for source_case,observed in zip(CASES,rows[0]):
  if observed["id"]!=source_case["id"] or len(observed["steps"])!=len(source_case["messages"]):raise ValueError("traces misaligned")
  results.append({"id":source_case["id"],"turns":[{"customer":message,**step}
    for message,step in zip(source_case["messages"],observed["steps"])]})
 return {"at":datetime.now(timezone.utc).isoformat(),"scenario_count":len(results),
   "turn_count":sum(len(x["turns"]) for x in results),"source_sha256":hashlib.sha256(text.encode()).hexdigest(),
   "candidate":source is not None,"environment":"NETWORKLESS_RUBY_REAL_REPLIES",
   "public_messages_sent":0,"real_orders":0,"api_calls":0,
   "stock_modified":False,"production_modified":False,"dialogues":results}
if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser()
 p.add_argument("--candidate",type=Path)
 p.add_argument("--output",type=Path,required=True)
 args=p.parse_args()
 source=args.candidate.read_text() if args.candidate else None
 result=run(source)
 _atomic_json(args.output,result)
 print(json.dumps({"scenarios":result["scenario_count"],"turns":result["turn_count"],
   "candidate":result["candidate"],"source_sha256":result["source_sha256"],
   "public_messages_sent":0,"real_orders":0},ensure_ascii=False))
