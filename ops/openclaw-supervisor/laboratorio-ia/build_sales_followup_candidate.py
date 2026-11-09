#!/usr/bin/env python3
"""Build a sales-only Ruby reply candidate using a frozen source SHA.

This is NOT a production deployment. Only produces candidate and unified diff
for review/test. The live bot is untouched, no API, no WAHA/Chatwoot.
"""
from pathlib import Path
from hashlib import sha256
from difflib import unified_diff
import json
from datetime import datetime,timezone

BOT=Path("/opt/softmobile-waha-test/frozen-sales-baseline/sales-bot-v2-1336f52fdf4d8e44.rb")
FROZEN_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
ANCHOR="      # SM_AUTO_POLICY_HOOK_END\n"
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE/"quality"/"sales-bot-v2-reply-candidate.rb"
DIFF=HERE/"quality"/"sales-bot-v2-reply-candidate.patch"
META=HERE/"quality"/"sales-bot-v2-reply-candidate.json"

ADDITIONS=r'''
      # SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN
      # Store no customer data and never commit a reservation, discount or price.
      # Deep-journey safety: a damaged delivered order is NOT a new repair sale.
      if t.match?(/\b(?:compre|comprado|pedido|me llego|recibi|venia)\b.{0,90}\b(?:quebrada|quebrado|golpeado|golpeada|roto|rota|danado|danada)\b/) ||
         t.match?(/\b(?:foto del dano|evidencia del dano|devolver el dinero|devolvieron el pago)\b/)
        return {reply:"Si el equipo llegó dañado, lo importante es revisar el reclamo de esa compra, no ofrecerte otra venta. Conservá fotos y comprobante; la solución y cualquier reembolso requieren verificación.",
          note:"RECLAMO DE ENTREGA: atención humana prioritaria; no derivar a reparaciones ni confirmar reembolso.",
          needs_human:true,intent: :complaint,tag:'deep_damaged_delivery'}
      end
      # Do not treat opt-out or no follow-up requests as new sales leads.
      if t.match?(/\b(?:no quiero comprar otro|no me ofrezcas|no quiero mas anuncios|no quiero seguimiento|no quiero mas ofertas|no me escribas|no me contactes|no quiero que me escribas|no me vas a escribir)\b/)
        return {reply:"Entendido, no querés nuevas ofertas ni seguimiento. Esa preferencia debe quedar registrada en la conversación para que se respete; no voy a proponerte más equipos aquí.",
          note:"OPOSICIÓN A CONTACTO: detener ofertas y marcar solicitud para que el operador configure no-contacto. No afirmar que ya fue guardada.",
          needs_human:true,intent: :cancel_interest,tag:'deep_no_followup'}
      end
      # Status of an earlier hold or refund can never be inferred from chat.
      if t.match?(/\b(?:ya quedo reservad[oa]|ya esta reservado|ya cancelaste|ya cancelaron todo|ya me devolvieron|ya se hizo el reembolso|ya mandaste la cotizacion|ya esta todo aprobado)\b/)
        return {reply:"Todavía no puedo confirmar ese estado: necesito comprobarlo en el registro correspondiente. No voy a decirte que quedó reservado, cancelado, pagado o enviado sin evidencia.",
          note:"ESTADO DE OPERACIÓN: verificar evidencia de reserva, cobro, cancelación, cotización o reembolso. No declarar ejecución.",
          needs_human:true,intent: :order_change,tag:'deep_status_unverified'}
      end
      # A bank-account image is not a phone photo; never fabricate bank details.
      if t.match?(/\b(?:imagen|foto|fotos)\b/) && t.match?(/\b(?:cuentas|datos bancarios|cuenta bancaria|bancos)\b/)
        return {reply:"La imagen de cuentas bancarias todavía debe verificarse con información oficial. No te pediré claves ni confirmaré pagos con una captura.",
          note:"CUENTAS DE COBRO: confirmar imagen y datos bancarios autorizados en canal seguro; no inventar.",
          needs_human:true,intent: :payments,tag:'deep_bank_image_unverified'}
      end
      # Direct request for a person must not imply a real transfer happened.
      if t.match?(/\b(?:hablar con una persona|atencion humana|hablar con alguien|necesito un humano)\b/)
        return {reply:"Claro. Tu solicitud de atención personal necesita una transferencia real para que alguien la atienda; todavía no puedo confirmarte que ya se haya realizado.",
          note:"ATENCIÓN PERSONAL: transferencia pendiente; no afirmar que se notificó a un empleado.",
          needs_human:true,intent: :human,tag:'deep_human_pending'}
      end
      # Financing approval requires an independent bank result.
      if t.match?(/\b(?:me aprueban el credito|credito automaticamente|banco me rechaza|me aprueba el banco|aprobacion automatica)\b/)
        return {reply:"La aprobación del crédito depende del banco y todavía no está confirmada. Primero hay que verificar plazo, requisitos y monto con información oficial.",
          note:"CRÉDITO: no confirmar aprobación, cuota ni tasa sin respuesta bancaria.",
          needs_human:true,intent: :finance,tag:'deep_credit_approval_unknown'}
      end
      # Answer photo questions safely while the photo bridge is deferred.
      if t.match?(/\b(?:foto|fotos|fotografia|fotografias|imagen|imagenes)\b/) &&
         !t.match?(/\b(?:reembolso|dano|danado|reclamo|queja|pantalla quebrada)\b/)
        descriptor=[device || 'equipo',cap && "de #{cap}",col && "en #{col.downcase}"].compact.join(' ')
        return {reply:"Las fotos reales del #{descriptor} aún no están confirmadas. Para mostrarte esa unidad exacta, primero deben verificarse las imágenes; no se han enviado desde esta consulta.",
          note:"FOTOS PENDIENTES: no usar genéricas ni afirmar envío, código o atención de encargado inexistentes.",
          needs_human:true,intent: :photos,tag:'deep_photos_unverified'}
      end
      # Shipping timeframe must not become an unverified handset price.
      if device && place && delivery_mode!='Retiro' &&
         t.match?(/\b(?:entonces cuanto tardaria|cuanto tardaria|cuanto demora|en cuantos dias|cuantos dias|en cuanto tiempo)\b/) &&
         !t.match?(/\b(?:mi pedido|mi envio|guia|rastreo|ya pague)\b/)
        return {reply:"Para entregar el #{device} en #{place}, todavía debo comprobar el plazo de transporte y disponibilidad. No tengo una fecha confirmada.",
          note:"ENVÍO: destino anterior conservado, plazo pendiente. No dar fechas inventadas.",
          needs_human:true,intent: :shipping,tag:'deep_shipping_time'}
      end
      # Explicit cancellation wins, including colloquial three-word changes of mind.
      if t.match?(/\b(?:mejor ya no quiero|ya no lo quiero|no voy a comprar|no sigo con la compra|cancelo(?: la compra)?|cancelame la compra)\b/) &&
         !t.match?(/\b(?:cancelo la reserva de otro|cancelo otra compra)\b/)
        return {reply:"Entendido, no sigo con esa compra. Si hiciste algún pago o apartado, revisamos el caso antes de confirmar una cancelación formal.",
          note:"CLIENTE CANCELA INTERÉS: detener oferta y seguimiento; si hay pago/apartado, derivar para revisión. No cancelar pedidos automáticamente.",
          needs_human:true,intent: :cancel_interest,tag:'sales_only_cancel_interest'}
      end
      # Buyer may use verbs with attached pronouns; keep the requested date.
      if device && ctx[:model] && ctx[:model][1] &&
         t.match?(/\b(?:apartarmelo|apartamelo|reservarmelo|reservamelo|guardarmelo|guardamelo|separarmelo|separamelo|apartas|apartamelo|apartenmelo|guardamelo)\b.{0,65}\b(?:manana|hoy|pasado manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b/) &&
         !t.match?(/\b(?:cancelo|cancelar|ya pague|ya lo reserve|ya lo aparte)\b/)
        weekday=t.match(/\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b/)
        requested=weekday ? {'miercoles'=>'miércoles','sabado'=>'sábado'}.fetch(weekday[1],weekday[1]) :
          (t.include?('manana') ? 'mañana' : 'hoy')
        return {reply:"Revisamos si podemos apartarte el #{device}#{cap ? ' de '+cap : ''} para #{requested}. Todavía no hay reserva confirmada: verifico existencia, precio y condiciones antes de coordinar. ¿Lo retirarías o lo necesitás con envío?",
          note:"RESERVA COLOQUIAL: fecha #{requested}; ningún apartado creado. Verificar condiciones comerciales y disponibilidad.",
          needs_human:true,intent: :reserve,tag:'sales_only_colloquial_reservation'}
      end
      # Shipping costs must not be mistaken for the handset price.
      if device && place && delivery_mode!='Retiro' &&
         t.match?(/\b(?:cuanto (?:me )?cobrari[ao]n por mandarmelo|cuanto (?:me )?cobran por (?:mandarmelo|enviarmelo|mandarlo)|cuanto costaria (?:mandarmelo|enviarmelo|mandarlo)|cuanto cuesta mandarmelo|precio del envio|tarifa de envio)\b/) &&
         !t.match?(/\b(?:mi pedido|ya pague|factura|reembolso|tracking|guia)\b/)
        return {reply:"Para mandarte el #{device} a #{place}, aún tengo que confirmar la tarifa de envío y la disponibilidad. No voy a darte un costo sin comprobarlo.",
          note:"COSTO DE ENVÍO: no confundir tarifa con precio del equipo. Verificar cobertura, tarifa y stock.",
          needs_human:true,intent: :shipping,tag:'sales_only_colloquial_shipping_cost'}
      end
      # Customer already gave destination; don't ask for it again.
      if device && place && delivery_mode!='Retiro' &&
         t.match?(/\b(?:cuantos dias se tarda|cuanto demora llegar|cuanto demora el envio|en cuanto tiempo llegaria|cuantos dias tardara|cuanto demora llegar a mi casa)\b/) &&
         !t.match?(/\b(?:mi pedido|mi envio|rastreo|guia|ya pague|ya enviaron)\b/)
        return {reply:"Para el envío del #{device} a #{place}, todavía no tengo un plazo confirmado. Debo verificar disponibilidad y transporte antes de darte una fecha.",
          note:"PLAZO DE ENVÍO: usar ciudad ya informada; nunca inventar fecha ni solicitarla otra vez.",
          needs_human:true,intent: :shipping,tag:'sales_only_colloquial_shipping_eta'}
      end
      # Never treat a customer's assertion as a bank credit approval.
      if t.match?(/\b(?:me aprobaron|ya me aprobaron|me han aprobado|aprobaron mi)\b.{0,40}\b(?:credito|financiamiento)\b/) ||
         t.match?(/\b(?:confirmas|confirmar|confirmame)\b.{0,50}\b(?:aprobaron|aprobar|aprobado)\b.{0,30}\b(?:credito|financiamiento)\b/)
        return {reply:"La aprobación del crédito todavía no está confirmada por el banco. Para continuar necesitamos verificar directamente el estado y las condiciones; no puedo darla por aprobada.",
          note:"FINANCIAMIENTO: no asumir aprobación bancaria ni pedir claves, códigos o datos sensibles.",
          needs_human:true,intent: :finance,tag:'sales_only_credit_status'}
      end
      # Explicit follow-up intent wins over a generic greeting/city question.
      if device && ctx[:model] && ctx[:model][1] &&
         t.match?(/\b(?:si es posible|si se puede|de ser posible|de estar aprobado|si lo autorizan|si me lo bajas|entonces si autorizan)\b.{0,75}\b(?:sigo con la compra|seguimos con la compra|seguimos|lo compro|cerramos(?: la compra)?|hacemos trato|me lo llevo)\b/)
        descriptor=[device,cap && "de #{cap}",col && "en #{col.downcase}"].compact.join(' ')
        return {reply:"Perfecto, seguimos con la cotización del #{descriptor}. La condición especial que pediste sigue pendiente de revisión, y tengo que confirmar precio final y existencia antes de cerrar. ¿Preferís retiro o envío?",
          note:"VENTAS: cliente confirma interés condicionado; verificar el contexto comercial anterior, cualquier descuento, margen, precio y stock. No asumir aprobación ni crear pedido.",
          needs_human:true,intent: :sales_followup,tag:'sales_only_offer_followup'}
      end
      if device && ctx[:model] && ctx[:model][1] &&
         t.match?(/\b(?:reservarlo|reservarla|reservar|apartar|apartarlo|apartas|apartarme|separarlo|separar|guardan|guardar)\b.{0,60}\b(?:manana|hoy|pasado manana|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b/) &&
         !t.match?(/\b(?:ya lo reserve|ya lo aparte|ya pague|cancelo|cancelar)\b/)
        weekday=t.match(/\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b/)
        requested=weekday ? {'miercoles'=>'miércoles','sabado'=>'sábado'}.fetch(weekday[1],weekday[1]) :
          (t.include?('pasado manana') ? 'pasado mañana' : (t.include?('manana') ? 'mañana' : 'hoy'))
        return {reply:"Podemos revisar el apartado del #{device}#{cap ? ' de '+cap : ''} para #{requested}, pero todavía no está reservado: antes debo verificar existencia, precio y condiciones. ¿Preferís retiro o envío?",
          note:"RESERVA: fecha solicitada #{requested}. Ninguna reserva realizada; verificar stock, condiciones, vigencia y autorización antes de prometer apartado.",
          needs_human:true,intent: :reserve,tag:'sales_only_reservation_followup'}
      end
      if device && place && delivery_mode!='Retiro' &&
         t.match?(/\b(?:en cuantos dias llegaria|en cuantos dias llegara|cuando llegaria|cuando llega|en cuanto tiempo llega|cuando estaria|cuantos dias tardaria|cuantos dias tarda|cuanto tarda el envio|cuanto tardaria el envio)\b/) &&
         !t.match?(/\b(?:mi pedido|mi envio|rastreo|guia|ya pague|ya enviaron)\b/)
        route_intro=delivery_mode=='Envío' ? "Para enviar el #{device} a #{place}" : "Si querés el #{device} con envío a #{place}"
        return {reply:"#{route_intro}, todavía no tengo días de entrega confirmados. Primero verifico existencia, transporte y plazo real; no quiero darte una fecha sin respaldo.",
          note:"ENVÍO: destino conservado #{place}. Verificar transportista, cobertura y disponibilidad. No inventar ETA ni volver a pedir la ciudad.",
          needs_human:true,intent: :shipping,tag:'sales_only_shipping_eta'}
      end
      if device && place && delivery_mode=='Envío' &&
         (t.match?(/\b(?:cuanto(?: me)? cuesta|cuanto(?: me)? cobran|cuanto sale|cuanto vale|cual es el costo)\b.{0,50}\b(?:enviarlo|enviarmelo|envio|enviar|mandarlo|mandarmelo)\b/) ||
          t.match?(/\b(?:enviarlo|envio|mandarlo|mandarmelo)\b.{0,40}\b(?:cuanto cobran|cuanto cuesta|cuanto vale|cuanto sale|costo)\b/)) &&
         !t.match?(/\b(?:mi pedido|ya envie|ya pague|pago|factura|reembolso)\b/)
        return {reply:"El costo de envío del #{device} a #{place} aún no está confirmado. Verifico disponibilidad, cobertura y tarifa de transporte antes de cotizarte ese cargo.",
          note:"COSTO DE ENVÍO: destino #{place}. Confirmar tarifa y stock; nunca confundir con precio del equipo.",
          needs_human:true,intent: :shipping,tag:'sales_only_shipping_cost'}
      end
      # Avoid robotic staff references for basic catalog questions. No
      # price or unit may be offered without an authorized stock/price source.
      if device && ctx[:model] && ctx[:model][1] &&
         [:price,:stock,:stock_price].include?(intent_type) &&
         !t.match?(/\b(?:envio|enviar|enviarlo|enviarmelo|mandarlo|mi pedido|ya pague|mi compra|reembolso)\b/)
        descriptor=[device,cap && "de #{cap}",col && "en #{col.downcase}"].compact.join(' ')
        if intent_type==:price
          response="Del #{descriptor}, todavía necesito confirmar el precio final de la unidad para cotizarte correctamente. No quiero darte un valor que después cambie."
        elsif intent_type==:stock
          response="Para el #{descriptor}, todavía necesito comprobar existencias reales y color antes de ofrecerte una unidad. Prefiero confirmártelo bien."
        else
          response="Para el #{descriptor}, necesito verificar precio y existencias de la misma unidad antes de cotizarte. Así evitamos darte información que no esté confirmada."
        end
        return {reply:response,
          note:"VENTAS: sin datos autorizados de precio/stock reales. Verificar SKU exacto, color, precio y existencia antes de cotizar.",
          needs_human:true,intent:intent_type,tag:'sales_only_stock_price_followup'}
      end
      # SALES_ONLY_FOLLOWUPS_CANDIDATE_END
'''
def make(base:str):
    if not isinstance(base,str) or sha256(base.encode()).hexdigest()!=FROZEN_SHA:
        raise ValueError("sales source drift: explicit audit needed")
    if base.count(ANCHOR)!=1 or "SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN" in base:
        raise ValueError("unexpected sales insertion anchor")
    candidate=base.replace(ANCHOR,ANCHOR+ADDITIONS,1)
    if candidate.count("SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN")!=1:
        raise ValueError("candidate injection invalid")
    return candidate

def main():
    raw=BOT.read_text()
    cand=make(raw)
    CANDIDATE.write_text(cand)
    diff="".join(unified_diff(raw.splitlines(keepends=True),
                              cand.splitlines(keepends=True),
                              fromfile="a/sales-bot-v2.rb",tofile="b/sales-bot-v2.rb"))
    DIFF.write_text(diff)
    META.write_text(json.dumps({
      "at":datetime.now(timezone.utc).isoformat(),
      "source_sha256":FROZEN_SHA,
      "candidate_sha256":sha256(cand.encode()).hexdigest(),
      "scope":"sales_only",
      "change_type":"review_only",
      "real_communications":0,"api_calls":0,"production_changed":False,
      "deployment_approved":False,
      "patch_lines_added":len(ADDITIONS.splitlines()),
      "patch_file":DIFF.name},indent=2)+"\n")
    print(json.dumps({"status":"candidate_only","source_pinned":True,
       "candidate_sha256":sha256(cand.encode()).hexdigest(),
       "patch_lines":len(ADDITIONS.splitlines()),"public_messages_sent":0}))
if __name__=="__main__":
    main()