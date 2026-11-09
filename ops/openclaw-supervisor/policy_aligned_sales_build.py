#!/usr/bin/env python3
"""Offline business-rule consolidation. Stage only; no customer sends.

Primary business policy: SoftMobile does NOT reserve / hold phones, and
no employee may claim an automatic booking or collect a hold deposit.
"""
from __future__ import annotations
import hashlib, difflib, json
from pathlib import Path

ROOT=Path("/opt/softmobile-waha-test")
ACTIVE=ROOT/"frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb"
PARENT=ROOT/"approved-sales-pilot/sales-pilot-a4ca83e5d83244eb.rb"
BUSINESS=ROOT/"knowledge/softmobile-business.json"
RULES=ROOT/"knowledge/reglas.md"
CATALOG=ROOT/"knowledge/catalogo.json"
OUT=ROOT/"approved-sales-pilot/candidates"
PARENT_SHA="a4ca83e5d83244eb8552c67ad55d291eb601440b9c94c4bd614cd7d28365c06d"
BASE_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
ANCHOR="      # REPLICA_SALES_GUARDS_BEGIN\n"
ADDITION=r"""      # BUSINESS_PLAYBOOK_20261106_NO_RESERVATIONS_BEGIN
      # No-contact requests outrank commercial follow-ups and reservations.
      if t.match?(/\b(?:no me envien mas ofertas|ya no me envien mas ofertas|no me manden mas ofertas|no quiero ofertas|no quiero recibir (?:mas )?(?:mensajes|publicidad)|no me contacten|no me escriban|dejar de recibir mensajes|no quiero seguimiento)\b/)
        return {reply:"Entendido. No te mandaré ofertas adicionales desde esta conversación. Registraremos tu solicitud de no contacto para impedir futuros seguimientos; no puedo confirmar aún que ya quedó registrada.",
          note:"CONSENTIMIENTO: solicitar supresión de contacto en el sistema; no crear seguimiento automático.",
          needs_human:true,intent: :cancel_interest,tag:'business_no_contact'}
      end
      # Customers' claims about deposits or bank approvals are not evidence.
      if t.match?(/\b(?:confirmas|confirmame|confirmar|verifica|revisa)\b.{0,48}\b(?:pago|transferencia|deposito)\b|\b(?:ya llego el pago|ya entro el pago|recibieron mi pago|llego mi transferencia)\b/)
        return {reply:"Todavía no tengo el pago confirmado. Primero hay que verificar el ingreso directamente en la cuenta oficial y relacionarlo con la compra; una captura no lo confirma.",
          note:"PAGO: cotejo bancario requerido antes de cobro, guía o despacho.",
          needs_human:true,intent: :payment_verification,tag:'business_payment_unverified'}
      end
      if t.match?(/\b(?:me aprobo|me aprobaron|me aprobaran|esta aprobado|me confirmas si (?:estoy )?aprobado)\b/) &&
         t.match?(/\b(?:bac|banco|credito|financiamiento|extrafinanciamiento|banrural|promerica|ficohsa)\b/)
        return {reply:"La aprobación del financiamiento todavía no está confirmada. Necesitamos verificar el resultado y las condiciones directamente con el banco antes de continuar.",
          note:"FINANCIAMIENTO: no asumir aprobación ni interés final sin verificación.",
          needs_human:true,intent: :finance,tag:'business_financing_unverified'}
      end
      # Discounts must preserve the documented gifts/margins approval gates.
      if t.match?(/\b4(?: por ciento)?\b/) && t.match?(/\b(?:descuento|rebaja|rebajar|bajar|bajas|bajas el precio)\b/)
        return {reply:"Un descuento del 4% requiere autorización previa del encargado y confirmación de las regalías incluidas. Por ahora no está aprobado; primero verificamos precio, existencia y margen.",
          note:"DESCUENTO 4%: autorización humana, margen, precio y accesorios confirmados.",
          needs_human:true,intent: :discount,tag:'business_discount_4_auth'}
      end
      if t.match?(/\b3(?: por ciento)?\b/) && t.match?(/\b(?:descuento|rebaja|rebajar|menos|sin accesorios)\b/)
        return {reply:"Podemos revisar un descuento de hasta el 3% sin accesorios, sujeto a precio y existencia verificados. Si preferís las cuatro regalías, usamos el precio de lista o el descuento normal de hasta 2%.",
          note:"DESCUENTO 3%: sin accesorios, calcular desde precio de lista confirmado.",
          needs_human:true,intent: :discount,tag:'business_discount_3_no_gifts'}
      end
      if t.match?(/\b2(?: por ciento)?\b/) && t.match?(/\b(?:descuento|rebaja|rebajar|menos|bajar|haces|das|aplicas)\b/)
        return {reply:"El descuento normal puede ser de hasta 2% y conserva las cuatro regalías: cobertor, vidrio templado, cargador y auriculares inalámbricos. Confirmamos primero el precio vigente y las existencias.",
          note:"DESCUENTO 2%: conservar cuatro regalías, cotizar solo con precio válido.",
          needs_human:true,intent: :discount,tag:'business_discount_2_gifts'}
      end
      if t.match?(/\bgarantia\b/) && t.match?(/\b(?:cuanto|cuantos|tiempo|dura|dias|meses|cubre)\b/)
        return {reply:"La garantía estándar es de 30 días para equipos usados y 60 días para nuevos, con diagnóstico de 1 a 5 días hábiles. Antes de comprar confirmamos las condiciones aplicables a la unidad que elijás.",
          note:"GARANTÍA: usar política comercial del 6-nov; no prometer reparación ni devolución sin evaluación.",
          needs_human:false,intent: :warranty,tag:'business_standard_warranty'}
      end
      # Photos are not physical phone holds. A photography status request must
      # address the photo workflow without claiming that media was delivered.
      if t.match?(/\b(?:fotos|imagenes|fotografias)\b/) && t.match?(/\b(?:apartad|reservad|guardad|separad)\w*\b/)
        return {reply:"Las fotos reales de esa unidad todavía no están confirmadas ni enviadas. Primero debemos verificar las imágenes correspondientes al modelo, capacidad y color de tu solicitud.",
          note:"FOTOS: no confundir estado de material con apartado comercial; validar código y variante.",
          needs_human:true,intent: :photos,tag:'business_photo_status_pending'}
      end
      # Formal SoftMobile policy: no holds, booking deposits or pre-reservations.
      # A request to cancel an existing order is a separate order-status action.
      if t.match?(/\b(?:apart(?:ad[oa]s?|ar|ame|amelo|armelo|armela|as|an|arlo|arla)?|reserv(?:a|as|ar|arlo|arla|arme|ame|amelo|armelo|ando|an|ad[oa]s?)?|guard(?:ar|ame|amelo|armelo|as|an|arlo|arla)|separ(?:ar|ame|amelo|armelo|as|an|arlo|arla)|anticipo(?:s)?)\b/) &&
         !t.match?(/\b(?:cancelar (?:mi |el )?(?:pedido|envio)|anular (?:mi |el )?pedido|devolucion de anticipo)\b/)
        return {reply:"En SoftMobile no hacemos reservas ni apartados, y no pedimos anticipos para guardar equipos. Cuando estés listo para comprar, confirmamos la existencia, precio y entrega de la unidad que buscás.",
          note:"POLÍTICA COMERCIAL: no apartar ni solicitar anticipos; validar unidad, precio y stock al comprar.",
          needs_human:false,intent: :reserve,tag:'business_no_reservations'}
      end
      # BUSINESS_PLAYBOOK_20261106_NO_RESERVATIONS_END
"""
def digest(b):return hashlib.sha256(b).hexdigest()
def make():
    if any(p.is_symlink() for p in (PARENT,ACTIVE,BUSINESS,RULES,CATALOG)):
        raise ValueError("symlink source not approved")
    if digest(PARENT.read_bytes())!=PARENT_SHA or digest(ACTIVE.read_bytes())!=BASE_SHA:
        raise ValueError("source SHA changed")
    commercial=json.loads(BUSINESS.read_text())
    catalog=json.loads(CATALOG.read_text())
    text=RULES.read_text(encoding="utf-8")
    if commercial.get("reservation_delivery",{}).get("reservations_allowed") is not False:
        raise ValueError("business playbook permits reservations")
    if len(catalog)!=97 or "SoftMobile no hace reservas ni apartados" not in text:
        raise ValueError("loaded November 6 policy/catalog not verified")
    source=PARENT.read_text(encoding="utf-8")
    if source.count(ANCHOR)!=1 or "BUSINESS_PLAYBOOK_20261106_NO_RESERVATIONS_BEGIN" in source:
        raise ValueError("ambiguous insertion or duplicate")
    dest=source.replace(ANCHOR,ANCHOR+ADDITION,1)
    if len(dest)>250000 or not dest.startswith(source.split(ANCHOR,1)[0]+ANCHOR):
        raise ValueError("source scope violation")
    if dest.split("      # BUSINESS_PLAYBOOK_20261106_NO_RESERVATIONS_END\n",1)[1] != source.split(ANCHOR,1)[1]:
        raise ValueError("other Ruby code was modified")
    suffix="\nif ENV['SM_MODE']=='test'\n"
    if dest.count(suffix)!=1 or source.count(suffix)!=1 or dest.split(suffix)[1]!=source.split(suffix)[1]:
        raise ValueError("public Ruby runner changed")
    if any(dest.count(k)!=1 for k in ("PILOT_CONVERSATION_ID = 3","AUTO_REPLY_LIMIT = 1")):
        raise ValueError("pilot guard missing")
    sha=digest(dest.encode())
    OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
    rb=OUT/("business-policy-"+sha[:16]+".rb")
    patch=OUT/("business-policy-"+sha[:16]+".patch")
    delta="".join(difflib.unified_diff(source.splitlines(True),dest.splitlines(True),
              fromfile="a/approved-sales-pilot.rb",tofile="b/business-policy-sales-pilot.rb"))
    if len(delta)>11000 or not delta:raise ValueError("patch out of bound")
    import os,tempfile
    for p,s in ((rb,dest),(patch,delta)):
        fd,tmp=tempfile.mkstemp(prefix=".staging-",dir=OUT)
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            f.write(s);f.flush();os.fsync(f.fileno())
        os.chmod(tmp,0o600);os.replace(tmp,p)
    if digest(rb.read_bytes())!=sha:raise ValueError("staged source hash mismatch")
    return {"status":"candidate_staged_for_policy_tests","candidate":str(rb),
            "patch":str(patch),"sha256":sha,"parent_sha256":PARENT_SHA,
            "production_modified":False,"whatsapp_messages":0,"catalog_variant_count":len(catalog),
            "no_reservations_enforced":True}
if __name__=="__main__":
    print(json.dumps(make(),ensure_ascii=False))