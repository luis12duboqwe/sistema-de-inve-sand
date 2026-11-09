#!/usr/bin/env python3
"""Three limited, reviewable Ruby dialogue fixes. Never touch the active Ruby source."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
from pathlib import Path

import replica_cycle

ROOT = Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill")
CANDIDATES = ROOT / "candidates"
BEGIN = "      # SALES_ONLY_FOLLOWUPS_CANDIDATE_BEGIN\n"
NEW_GUARD = r"""      # REPLICA_SALES_GUARDS_BEGIN
      # Explicit no-contact requests override all sales prompts; registration is pending.
      if t.match?(/\b(?:no me escriban(?: mas| de nuevo)?|no me manden mas ofertas|quiero dejar de recibir mensajes|no me contacten(?: mas)?|no deseo mas publicidad|no quiero recibir mas mensajes)\b/)
        return {reply:"Entendido, no querés recibir más mensajes ni ofertas. No voy a seguir ofreciéndote equipos aquí. La solicitud de no contacto debe registrarse para detener futuros seguimientos; aún no puedo confirmar que ya quedó registrada.",
          note:"NO CONTACTO: detener ofertas; marcar supresión y pedir confirmación humana en el sistema, sin asumir que se guardó.",
          needs_human:true,intent: :cancel_interest,tag:'replica_stop_contact'}
      end
      # Customer-reported transfer is NOT proof of a received payment.
      if t.match?(/\b(?:ya te transferi|ya transferi|me confirmas que pague|ya hice el deposito|ya hice el pago|recibieron el pago|envie la transferencia|confirmas la recepcion)\b/)
        return {reply:"Gracias por avisar del pago. Primero tenemos que comprobar en la cuenta oficial si se recibió la transferencia o depósito y asociarlo con tu compra. Por ahora el pago no está confirmado.",
          note:"PAGO PENDIENTE DE VALIDAR: no confirmar transferencia, no crear recibo ni pedir claves; revisión interna.",
          needs_human:true,intent: :payment_verification,tag:'replica_payment_pending'}
      end
      # Bank approval status must be checked, never inferred from the customer's question.
      if t.match?(/\b(?:el credito esta aprobado|ya esta aprobado mi financiamiento|me confirmas que fue aprobada|me confirmas si me aprobaron el credito|aprobacion bancaria confirmada)\b/)
        return {reply:"La aprobación del crédito todavía no está confirmada. Necesitamos verificar directamente el resultado con el banco; no puedo darlo por aprobado ni prometer cuotas hasta comprobar las condiciones.",
          note:"BANCO: consulta sobre aprobación; estado pendiente, validar con institución financiera.",
          needs_human:true,intent: :finance,tag:'replica_bank_unverified'}
      end
      # REPLICA_SALES_GUARDS_END
"""

def digest(s):
    return hashlib.sha256(s.encode("utf-8") if isinstance(s, str) else s).hexdigest()

def improve(source: str) -> str:
    if source.count(BEGIN) != 1 or "REPLICA_SALES_GUARDS_BEGIN" in source:
        raise replica_cycle.Blocked("missing safe insertion point or already applied")
    revised = source.replace(BEGIN, BEGIN + NEW_GUARD, 1)
    if len(revised) > 245000 or not revised.startswith(source.split(BEGIN, 1)[0] + BEGIN):
        raise replica_cycle.Blocked("source modification outside allowlisted insertion")
    if revised.split("      # REPLICA_SALES_GUARDS_END\n", 1)[1] != source.split(BEGIN, 1)[1]:
        raise replica_cycle.Blocked("source suffix changed")
    if "PILOT_CONVERSATION_ID = 3" not in revised or "AUTO_REPLY_LIMIT = 1" not in revised:
        raise replica_cycle.Blocked("pilot safety marker removed")
    return revised

def create():
    meta, original, parent = replica_cycle.preflight()
    old = parent.read_text(encoding="utf-8")
    new = improve(old)
    sha = digest(new)
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    path = CANDIDATES / ("review-" + sha[:16] + ".rb")
    patch = CANDIDATES / ("review-" + sha[:16] + ".patch")
    diff = "".join(difflib.unified_diff(
        original.decode("utf-8").splitlines(True), new.splitlines(True),
        fromfile="a/sales-bot-v2.rb", tofile="b/sales-bot-v2.rb"))
    if not diff or len(diff) > 25000:
        raise replica_cycle.Blocked("candidate patch exceeds limit")
    replica_cycle.write_atomic(path, new)
    replica_cycle.write_atomic(patch, diff)
    if digest(path.read_text(encoding="utf-8")) != sha:
        raise replica_cycle.Blocked("candidate staging corrupt")
    metadata = {"status": "awaiting_independent_qa", "source_sha256": digest(original),
                "parent_candidate_sha256": digest(old), "candidate_sha256": sha,
                "candidate_file": str(path), "patch_file": str(patch),
                "recipes": ["contact_optout", "unverified_payment", "unverified_bank_approval"],
                "auto_deploy": False, "public_messages_sent": 0,
                "manual_review_required": True}
    replica_cycle.write_atomic(CANDIDATES / "latest.json", replica_cycle.to_json(metadata))
    return metadata

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--make",action="store_true")
    args=ap.parse_args()
    if not args.make:
        ap.error("use --make")
    print(json.dumps(create(),ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())