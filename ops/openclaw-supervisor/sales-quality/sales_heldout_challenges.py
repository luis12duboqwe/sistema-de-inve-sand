#!/usr/bin/env python3
"""Held-out buyer rephrasing challenges for isolated Ruby sales candidate.

These 18 prompts are separate from the fixed 72-dialogue candidate design set.
All fictional. Score actual Ruby replies, never mock checkouts or message sends.
"""
from datetime import datetime,timezone
from pathlib import Path
from hashlib import sha256
import json,re
from inventory_quality_lab import grouped
from inventory_training_lab import parse_with_real_ruby
from quality_auditor import _atomic_json
from sales_conversation_quality import fold, CITY_REPEAT

DEVICE="Busco iPhone 14 Pro Max de 256 GB negro"
CHALLENGES=[
 ("negotiation","¿Me hacés una rebaja?", "De ser posible hacemos trato",None),
 ("negotiation","¿Se puede mejorar el precio?", "Si me lo bajás, lo compro",None),
 ("negotiation","¿Hay descuento de contado?", "Entonces si autorizan el precio me lo llevo",None),
 ("negotiation","¿Me rebajás 500 lempiras?", "Si se puede, seguimos",None),
 ("negotiation","¿Podemos ajustar el precio?", "Me sirve si autorizan la rebaja",None),
 ("negotiation","¿Cuál es el mejor precio?", "De estar aprobado, cerramos la compra",None),
 ("reservation","¿Me lo pueden apartar?", "¿Me lo apartás para el lunes?","lunes"),
 ("reservation","¿Se puede reservar?", "¿Puedo reservarlo hasta mañana por la tarde?","manana"),
 ("reservation","¿Me lo pueden separar?", "¿Lo podés apartar hoy?","hoy"),
 ("reservation","¿Se pueden hacer reservas?", "¿Se podrá separar para el sábado?","sabado"),
 ("reservation","¿Aceptan apartados?", "¿Me lo guardan hasta mañana?","manana"),
 ("reservation","¿Puedo apartarlo?", "Quiero reservar para mañana","manana"),
 ("shipping","¿Hacen envíos a San Pedro Sula?", "¿Cuánto me cobran para mandarlo?","san pedro sula"),
 ("shipping","¿Lo mandan a Choloma?", "¿Y cuánto se cobra de envío?","choloma"),
 ("shipping","¿Lo pueden mandar a Choloma?", "¿En cuánto tiempo llega?","choloma"),
 ("shipping","¿Hacen envíos a Choloma?", "¿Cuándo estaría por allá?","choloma"),
 ("shipping","¿Pueden enviar a Villanueva?", "¿Cuánto me cuesta mandarlo?","villanueva"),
 ("shipping","¿Hacen envíos a Tegucigalpa?", "¿Cuánto tarda el envío?","tegucigalpa"),
]

def items():
    assert len(CHALLENGES)==18
    return [{"id":f"holdout-{i:02d}",
             "family":family,
             "messages":[DEVICE,init,last],
             "destination":dest}
            for i,(family,init,last,dest) in enumerate(CHALLENGES)]

def score(task,trace):
    if trace.get("id")!=task["id"] or len(trace.get("steps",[]))!=3:
        raise ValueError("invalid holdout trace")
    reply=fold(trace["steps"][-1].get("baseline",""))
    family=task["family"]
    if family=="negotiation":
        good=(bool(re.search(r"\b(?:precio|rebaja|descuento|cotiza|condicion|compra)\w*\b",reply))
              and bool(re.search(r"\b(?:verific|confirm|revis|pendiente|antes de)\w*",reply))
              and not CITY_REPEAT.search(reply))
    elif family=="reservation":
        good=(bool(re.search(r"\b(?:reserv|apart|separ)\w*",reply))
              and task["destination"] in reply
              and bool(re.search(r"\b(?:verific|confirm|revis|pendiente|antes de|todavia)\w*",reply)))
    else:
        good=(task["destination"] in reply and
              bool(re.search(r"\b(?:envio|transport|entreg|tarifa|plazo|costo)\w*",reply))
              and not CITY_REPEAT.search(reply))
    promised=bool(re.search(r"\b(?:ya esta reservado|ya quedo apartado|entrega garantizada|descuento aprobado|pago confirmado)\b",reply))
    return {"id":task["id"],"family":family,"passed":bool(good and not promised),
            "promised":promised}

def run(source=None):
    tasks=items()
    actual=[]
    for block in grouped(tasks,15):
        traces=parse_with_real_ruby([
            {"id":r["id"],"messages":r["messages"],"expected":"not_found"}
            for r in block],source=source)
        if len(traces)!=len(block):raise ValueError("incomplete")
        actual.extend(score(t,tr) for t,tr in zip(block,traces))
    return {
       "at":datetime.now(timezone.utc).isoformat(),
       "environment":"HELDOUT_SYNTHETIC_RUBY_ONLY",
       "source_sha256":sha256(source.encode()).hexdigest() if source is not None else
          sha256(Path("/opt/softmobile-waha-test/sales-bot-v2.rb").read_bytes()).hexdigest(),
       "candidate":source is not None,
       "scenarios":len(actual),"passed":sum(r["passed"] for r in actual),
       "failed_ids":[r["id"] for r in actual if not r["passed"]],
       "by_family":{k:{"tested":sum(r["family"]==k for r in actual),
                       "passed":sum(r["family"]==k and r["passed"] for r in actual)}
                    for k in ("negotiation","reservation","shipping")},
       "public_messages_sent":0,"real_sales":0,
       "production_modified":False,"api_calls":0}
if __name__=="__main__":
    import sys
    source=Path(sys.argv[1]).read_text() if len(sys.argv)>1 else None
    print(json.dumps(run(source),ensure_ascii=False))
