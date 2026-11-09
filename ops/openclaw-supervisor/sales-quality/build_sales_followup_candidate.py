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

BOT=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
FROZEN_SHA="1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
ANCHOR="      # SM_AUTO_POLICY_HOOK_END\n"
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE/"quality"/"sales-bot-v2-reply-candidate.rb"
DIFF=HERE/"quality"/"sales-bot-v2-reply-candidate.patch"
META=HERE/"quality"/"sales-bot-v2-reply-candidate.json"

ADDITIONS=r'''
      # SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN
      # Store no customer data and never commit a reservation, discount or price.
      # Explicit follow-up intent wins over a generic greeting/city question.
      if device && ctx[:model] && ctx[:model][1] &&
         t.match?(/\b(?:si es posible|si se puede)\b.{0,65}\b(?:sigo con la compra|seguimos con la compra|lo compro|cerramos)\b/)
        descriptor=[device,cap && "de #{cap}",col && "en #{col.downcase}"].compact.join(' ')
        return {reply:"Perfecto, seguimos con la cotización del #{descriptor}. La condición especial que pediste sigue pendiente de revisión, y tengo que confirmar precio final y existencia antes de cerrar. ¿Preferís retiro o envío?",
          note:"VENTAS: cliente confirma interés condicionado; verificar el contexto comercial anterior, cualquier descuento, margen, precio y stock. No asumir aprobación ni crear pedido.",
          needs_human:true,intent: :sales_followup,tag:'sales_only_offer_followup'}
      end
      if device && ctx[:model] && ctx[:model][1] &&
         t.match?(/\b(?:reservarlo|reservarla|apartar|apartarlo|separarlo)\b.{0,40}\b(?:manana|hoy|pasado manana)\b/) &&
         !t.match?(/\b(?:ya lo reserve|ya lo aparte|ya pague|cancelo|cancelar)\b/)
        requested=t.include?('pasado manana') ? 'pasado mañana' : (t.include?('manana') ? 'mañana' : 'hoy')
        return {reply:"Podemos revisar el apartado del #{device}#{cap ? ' de '+cap : ''} para #{requested}, pero todavía no está reservado: antes debo verificar existencia, precio y condiciones. ¿Preferís retiro o envío?",
          note:"RESERVA: fecha solicitada #{requested}. Ninguna reserva realizada; verificar stock, condiciones, vigencia y autorización antes de prometer apartado.",
          needs_human:true,intent: :reserve,tag:'sales_only_reservation_followup'}
      end
      if device && place && delivery_mode=='Envío' &&
         t.match?(/\b(?:en cuantos dias llegaria|en cuantos dias llegara|cuando llegaria|cuando llega|cuantos dias tardaria|cuantos dias tarda)\b/) &&
         !t.match?(/\b(?:mi pedido|mi envio|rastreo|guia|ya pague|ya enviaron)\b/)
        return {reply:"Para enviar el #{device} a #{place}, todavía no tengo días de entrega confirmados. Primero verifico existencia, transporte y plazo real; no quiero darte una fecha sin respaldo.",
          note:"ENVÍO: destino conservado #{place}. Verificar transportista, cobertura y disponibilidad. No inventar ETA ni volver a pedir la ciudad.",
          needs_human:true,intent: :shipping,tag:'sales_only_shipping_eta'}
      end
      if device && place && delivery_mode=='Envío' &&
         t.match?(/\b(?:cuanto cuesta|cuanto sale|cuanto vale|cual es el costo)\b.{0,38}\b(?:enviarlo|enviarmelo|envio|enviar|mandarlo|mandarmelo)\b/) &&
         !t.match?(/\b(?:mi pedido|ya envie|ya pague|pago|factura|reembolso)\b/)
        return {reply:"El costo de envío del #{device} a #{place} aún no está confirmado. Verifico disponibilidad, cobertura y tarifa de transporte antes de cotizarte ese cargo.",
          note:"COSTO DE ENVÍO: destino #{place}. Confirmar tarifa y stock; nunca confundir con precio del equipo.",
          needs_human:true,intent: :shipping,tag:'sales_only_shipping_cost'}
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
