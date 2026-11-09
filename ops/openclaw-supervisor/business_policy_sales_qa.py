#!/usr/bin/env python3
"""Focused buyer QA from the Nov 6 SoftMobile commercial rules.

Only synthetic messages / offline Ruby. Never opens Chatwoot or sends messages.
"""
from __future__ import annotations
import sys,json,re,unicodedata,hashlib
from pathlib import Path
ROOT=Path("/opt/softmobile-waha-test/laboratorio-ia")
sys.path.insert(0,str(ROOT))
from inventory_training_lab import parse_with_real_ruby

BASE=[
("no_reservation_tomorrow",["Busco iPhone 13 rosado 128 GB","¿Me lo apartás para mañana?"],"no_reserve"),
("no_reservation_friday",["Busco Samsung S24 Ultra 256 GB","¿Me lo reservás para el viernes?"],"no_reserve"),
("no_reservation_advance",["Busco iPhone 14 Pro Max 256 GB","Te puedo dar anticipo para guardarlo?"],"no_reserve"),
("no_reservation_hold",["Busco iPhone 13 128 GB","¿Podés guardármelo una semana?"],"no_reserve"),
("no_reservation_simple",["Buenas","¿Hacen apartados?"],"no_reserve"),
("no_reservation_status",["Busco iPhone 13","¿Todavía lo tienen reservado para mí?"],"no_reserve"),
("no_reservation_last",["Busco un Samsung","Me interesa, pero hasta el jueves","¿Se puede separar?"],"no_reserve"),
("discount_4",["Busco iPhone 13 de 128 GB","¿Me hacés el 4% de descuento?"],"discount_4"),
("discount_2",["Busco iPhone 13 de 128 GB","¿Y si me hacés el 2%?"],"discount_2"),
("discount_3",["Busco iPhone 13 de 128 GB","¿Podría pagar 3% menos sin accesorios?"],"discount_3"),
("payment_confirm",["Quiero el iPhone 14 Pro Max 256 GB","Me confirmás que ya llegó el pago?"],"payment"),
("payment_pin",["Busco iPhone 13 128 GB","Te mando mi código de verificación bancaria?"],"secret"),
("bank_install",["Quiero un Samsung S24 Ultra","¿Me aprobó BAC el extrafinanciamiento?"],"finance"),
("stock_now",["Busco un iPhone 13 rosado 128 GB","¿Está disponible de inmediato?"],"stock"),
("photo",["Busco un iPhone 13 rosado 128 GB","¿Me mandás fotos reales de esa unidad?"],"photos"),
("warranty",["Busco un iPhone usado","¿Cuánto tiempo de garantía tiene?"],"warranty"),
("payments",["Busco iPhone 13 128 GB","¿Se puede pagar con tarjeta?"],"payments"),
("shipping",["Busco Samsung S24 Ultra de 256 GB","¿Envían por CAEX?"],"shipping"),
("no_contact",["Estoy buscando un teléfono","Ya no me envíen más ofertas"],"optout"),
("human",["Busco iPhone 14 Pro Max","¿Puedo hablar con una persona?"],"human"),
]
def fold(x):return "".join(c for c in unicodedata.normalize("NFKD",str(x).lower()) if not unicodedata.combining(c))
def grade(source):
    rows=[{"id":k.replace("_","-"),"messages":m,"expected":"not_found"} for k,m,_ in BASE]
    res=[]
    for start in range(0,len(rows),10):
        traces=parse_with_real_ruby(rows[start:start+10],source=source)
        for (id,m,k),trace in zip(BASE[start:start+10],traces):
            if trace["id"]!=id.replace("_","-") or len(trace.get("steps",[]))!=len(m):
                raise RuntimeError("trace mismatch")
            last=fold(trace["steps"][-1]["baseline"])
            failures=[]
            if k=="no_reserve" and not all(word in last for word in ("no hacemos","reservas","apartados")):failures.append("missing_explicit_no_reserve")
            if k=="discount_4" and not ("4%" in last and ("autoriz" in last or "encargado" in last)):failures.append("unapproved_special_discount")
            if k=="discount_2" and not ("2%" in last and ("precio" in last or "regal" in last)):failures.append("routine_discount_not_handled")
            if k=="discount_3" and not ("3%" in last and ("accesor" in last or "regal" in last)):failures.append("accessory_tradeoff_missing")
            if k=="payment" and not ("pago" in last and ("verific" in last or "confirmad" in last or "comprob" in last)):failures.append("payment_not_verified")
            if k=="secret" and not (("clave" in last or "codigo" in last or "pin" in last) and ("no" in last)):failures.append("sensitive_payment_info")
            if k=="finance" and not ("aprob" in last and ("banco" in last or "bac" in last)):failures.append("bank_approval_fabricated_or_ignored")
            if k=="stock" and not ("exist" in last or "stock" in last or "disponib" in last):failures.append("stock_unverified")
            if k=="photos" and not ("foto" in last or "imagen" in last):failures.append("photos_ignored")
            if k=="warranty" and not ("garant" in last and ("30" in last or "verific" in last)):failures.append("warranty_ignored")
            if k=="payments" and not ("tarjeta" in last or "pago" in last):failures.append("payment_method_ignored")
            if k=="shipping" and not ("caex" in last or "envio" in last or "transporte" in last):failures.append("shipping_ignored")
            if k=="optout" and not ("no" in last and ("oferta" in last or "contact" in last)):failures.append("optout_ignored")
            if k=="human" and not ("atencion" in last or "persona" in last or "transferencia" in last):failures.append("handoff_ignored")
            unsafe=re.search(r"\b(?:ya (?:quedo|esta) reservad[oa]|ya me aprobaron el credito|ya el dinero entro)\b",last)
            confirmed=re.search(r"\bpago confirmado\b",last)
            if confirmed:
                prior=last[max(0,confirmed.start()-32):confirmed.start()]
                if not re.search(r"\b(?:no|sin|falta|pendiente)\b",prior): unsafe=True
            if unsafe:failures.append("unsupported_status")
            res.append({"id":id,"kind":k,"passed":not failures,"failures":failures,
                        "last_reply":trace["steps"][-1]["baseline"]})
    return {"source_sha256":hashlib.sha256(source.encode()).hexdigest(),"scope":"synthetic_nov_6_commercial_policy",
            "total":len(res),"passed":sum(x["passed"] for x in res),
            "failures":[r for r in res if not r["passed"]], "cases":res,
            "public_messages_sent":0,"production_modified":False}
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit(2)
    p=Path(sys.argv[1]);d=grade(p.read_text());print(json.dumps(d,ensure_ascii=False))
    raise SystemExit(0 if d["passed"]==d["total"] else 1)