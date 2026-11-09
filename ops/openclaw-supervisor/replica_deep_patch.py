#!/usr/bin/env python3
"""Scope-bounded offline deep conversation improvements, never a deploy action.

Only the SHA-pinned Replica candidate is an eligible parent. Staged result
is accepted only if the full deep, existing and independent suites pass.
"""
from __future__ import annotations
import difflib, hashlib, json
from pathlib import Path
from replica_cycle import write_atomic

BASE=Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill")
PARENT=BASE/"candidates/review-367912aab2611f22.rb"
PARENT_SHA="367912aab2611f22392cb842c5c0076cc601c7e1c0320300b7f352b9625c5b4b"
LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
LIVE_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
ROOT=BASE/"candidates"
MARK="      # REPLICA_SALES_GUARDS_END\n"
CTX="      texts.each do |str|\n"
CONTEXT_INSERT=r"""      last_explicit_pro_max=nil
      texts.each do |str|
        # Shorthand "regreso al Pro Max" may only restore a previously and
        # explicitly named device. Never infer a number or brand from nothing.
        nt_revert=normalize(str)
        if nt_revert.match?(/\b(?:regreso|vuelvo|volvemos)\s+(?:al|a)\s+(?:pro\s*max)\b/) && last_explicit_pro_max
          data[:model]=last_explicit_pro_max
          data[:capacity]=nil
          data[:color]=nil
          data[:color_options]=[]
        end
"""
# Existing model(...) block must update this witnessed previous model once
# it recognizes a real full device, not via a recent generic "pro max".
CTX_MODEL_OLD="            data[:model]=new_model\n          elsif !data[:model]"
CTX_MODEL_NEW="""            data[:model]=new_model
            last_explicit_pro_max=new_model if new_model[0]==:iphone && new_model[1] && new_model[2]=='pro max'
          elsif !data[:model]"""
GUARDS=r"""      # REPLICA_DEEP_SALES_V1_BEGIN
      # Explicit sensitive questions must not fall through to model/GB questions.
      if t.match?(/\b(?:clave temporal|codigo temporal|codigo de verificacion|pin bancario|clave del banco|otp|cvv)\b/)
        return {reply:"No compartás ni enviés claves, PIN ni códigos bancarios temporales por este chat. Para verificar un pago usamos únicamente el canal autorizado, sin solicitar credenciales.",
          note:"SEGURIDAD BANCARIA: no solicitar códigos ni credenciales.",needs_human:true,intent: :payment_safety,tag:'replica_deep_security'}
      end
      if t.match?(/\b(?:me confirmas (?:que |si )?(?:el )?pago (?:entro|llego|fue recibido)|confirmame (?:el|si recibieron el) pago|pago (?:ya )?(?:entro|fue recibido))\b/)
        return {reply:"El pago todavía no está confirmado. Tenemos que verificar el ingreso real en la cuenta oficial y vincularlo con la compra antes de confirmarlo.",
          note:"PAGO NO VERIFICADO: cotejo bancario pendiente; no asumir fondos recibidos.",needs_human:true,intent: :payment_verification,tag:'replica_deep_payment'}
      end
      if t.match?(/\b(?:ya mandaste|mandaron|enviaron|ya enviaron|ya mandaron)\s+(?:la |mi |una )?cotizaci[oó]n\b/)
        return {reply:"Todavía no tengo confirmación de que la cotización se haya enviado. Primero hay que verificar precio, existencias y el registro de envío para darte una respuesta correcta.",
          note:"COTIZACIÓN: ninguna salida ni precio verificado; cotejar registro.",needs_human:true,intent: :price,tag:'replica_deep_quote_status'}
      end
      if t.match?(/\b(?:segu[ií]s|siguen|seguimos)\s+reserv[a-z]*|todav[ií]a\s+(?:lo |la )?(?:tienen )?reservad[oa]/)
        return {reply:"No tengo una reserva confirmada. Si pediste cancelar, hay que verificar el estado de esa solicitud antes de continuar; no voy a asumir que sigue reservado.",
          note:"RESERVA/CANCELACIÓN: comprobar registro; no continuar cobro o apartado sin consentimiento.",needs_human:true,intent: :reserve,tag:'replica_deep_reservation_status'}
      end
      if t.match?(/\b(?:me lo|lo|la)\s+(?:reservan|reservas|apartan|apartas)\s+(?:para )?(?:manana|hoy|el lunes|el martes|el miercoles|el jueves|el viernes|el sabado|el domingo)\b/)
        requested_day=t[/\b(?:manana|hoy|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b/] || 'el día solicitado'
        return {reply:"Puedo revisar las condiciones para apartarlo para #{requested_day}, pero todavía no está reservado. Antes debemos verificar existencia y si se aceptan apartados.",
          note:"RESERVA: fecha solicitada; sin acción real hasta confirmar políticas y existencia.",needs_human:true,intent: :reserve,tag:'replica_deep_reservation_request'}
      end
      if t.match?(/\b(?:cancelar|cancelacion|anular)\b.{0,45}\b(?:antes|despach|salir|envio|pedido)\b|\bantes\b.{0,35}\b(?:cancelar|anular)\b/)
        return {reply:"Podemos revisar si el pedido se puede cancelar antes del despacho. Hay que verificar si ya fue enviado y qué condiciones aplican; no puedo confirmar la cancelación todavía.",
          note:"CANCELACIÓN DE ENVÍO: comprobar estado de despacho y política aplicable.",needs_human:true,intent: :order_change,tag:'replica_deep_cancel_shipping'}
      end
      if t.match?(/\b(?:contra entrega|pagar al recibir|pago al recibir|pagar cuando (?:me )?llegue)\b/)
        destination=place ? " para #{place}" : ""
        return {reply:"El pago contra entrega#{destination} no está confirmado como opción. Necesitamos verificar el método de pago y las condiciones del envío antes de aceptarlo.",
          note:"PAGO Y ENVÍO: verificar contraentrega y destino, sin solicitar pago ni repetir ciudad.",needs_human:true,intent: :payments,tag:'replica_deep_cod'}
      end
      if t.match?(/\bpromerica\b/) && t.match?(/\b(?:mismos|plazos|cuotas|meses|extrafinanciamiento|financiamiento)\b/)
        return {reply:"Con Promerica los plazos y condiciones de financiamiento pueden ser distintos. Debemos verificar los meses disponibles y la aprobación con el banco; no hay cuota confirmada.",
          note:"PROMERICA: verificar tasa, plazo y aprobación con el banco.",needs_human:true,intent: :finance,tag:'replica_deep_promerica'}
      end
      if t.match?(/\b(?:pasos|que sigue|como hago|que necesito|como continuamos)\b.{0,48}\b(?:comprar|compra|seguir|continuar)\b/)
        return {reply:"Para continuar con la compra del #{name}, necesitamos verificar la unidad exacta, precio, existencia y forma de entrega. Con esos datos confirmados podemos seguir con el pedido, sin solicitar pago anticipado.",
          note:"COMPRA: confirmar datos reales antes de cerrar. No crear orden ni aceptar pago.",needs_human:true,intent: :purchase,tag:'replica_deep_purchase_steps'}
      end
      if t.match?(/\b(?:ok|dale|listo|bien|si)\s+(?:ya )?(?:lo )?(?:compro|compro hoy|quiero comprarlo)\b/)
        return {reply:"Perfecto, seguimos con la compra del #{name}. El siguiente paso es verificar precio final, existencia y modalidad de entrega antes de confirmar el pedido. Por ahora no hay una venta aprobada.",
          note:"CIERRE: comprador listo, validar condiciones reales sin repetir ciudad.",needs_human:true,intent: :purchase,tag:'replica_deep_ready_to_buy'}
      end
      # REPLICA_DEEP_SALES_V1_END
"""
def sha(data):return hashlib.sha256(data).hexdigest()
def build():
    if sha(LIVE.read_bytes())!=LIVE_SHA: raise ValueError("active Ruby source changed")
    raw=PARENT.read_bytes()
    if sha(raw)!=PARENT_SHA: raise ValueError("parent candidate drift")
    source=raw.decode("utf-8")
    if any(source.count(x)!=1 for x in (CTX,MARK,CTX_MODEL_OLD)):
        raise ValueError("anchors ambiguous")
    if "REPLICA_DEEP_SALES_V1_BEGIN" in source:
        raise ValueError("already applied")
    source=source.replace(CTX,CONTEXT_INSERT,1)
    source=source.replace(CTX_MODEL_OLD,CTX_MODEL_NEW,1)
    source=source.replace(MARK,GUARDS+MARK,1)
    if not 1000<len(source)<250000:
        raise ValueError("candidate source length outside bounds")
    # Two strict insertions and one limited model-history assignment. Never
    # touch Ruby source beyond this isolated candidate.
    digest=sha(source.encode())
    output=ROOT/f"deep-review-{digest[:16]}.rb"
    diff=ROOT/f"deep-review-{digest[:16]}.patch"
    patch="".join(difflib.unified_diff(
        LIVE.read_text().splitlines(True),source.splitlines(True),
        fromfile="a/sales-bot-v2.rb",tofile="b/sales-bot-v2.rb"))
    if not patch or len(patch)>45000: raise ValueError("diff too long")
    if sha(LIVE.read_bytes())!=LIVE_SHA:
        raise ValueError("active source changed during staging")
    # Atomic rename replaces any stale path without following existing symlinks.
    write_atomic(output,source)
    write_atomic(diff,patch)
    if sha(output.read_bytes())!=digest or output.is_symlink() or diff.is_symlink():
        raise ValueError("staged source integrity failed")
    return {"mode":"offline_candidate_only","parent_sha256":PARENT_SHA,
            "source_sha256":LIVE_SHA,"candidate_sha256":digest,
            "candidate_file":str(output),"patch_file":str(diff),
            "public_messages_sent":0,"production_changed":False,
            "auto_deploy":False,"ready_for_review":False}
if __name__=="__main__":
    print(json.dumps(build(),ensure_ascii=False))