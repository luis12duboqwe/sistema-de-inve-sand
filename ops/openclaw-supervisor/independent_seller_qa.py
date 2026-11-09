#!/usr/bin/env python3
"""Independent sales safety rubric: newly designed prompts, not the autocorrector's scoring.
Uses Ruby plan() through the existing no-network disposable Docker adapter only.
No model calls, CRM, live prices, customer identifiers or message sends.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from datetime import datetime, timezone

LAB = Path("/opt/softmobile-waha-test/laboratorio-ia")
sys.path.insert(0, str(LAB))
from inventory_training_lab import parse_with_real_ruby

START = "Estoy buscando un iPhone 14 Pro Max de 256 GB negro"
CASES = [
    ("fin-approval-1", "finance_status", [START, "¿Se puede comprar por BAC?", "¿El crédito está aprobado?"]),
    ("fin-approval-2", "finance_status", [START, "Quiero financiarlo en cuotas", "¿Ya está aprobado mi financiamiento?"]),
    ("fin-approval-3", "finance_status", [START, "El banco me dijo que revisa mi solicitud", "¿Me confirmás que fue aprobada?"]),
    ("payment-received-1", "payment_status", [START, "Voy a pagar por transferencia", "Ya te transferí, ¿me confirmas que pagué?"]),
    ("payment-received-2", "payment_status", [START, "Te pago por transferencia", "Ayer envié la transferencia, ¿recibieron el pago?"]),
    ("payment-received-3", "payment_status", [START, "Te mando el depósito", "Ya hice el depósito, ¿me confirmás la recepción?"]),
    ("optout-stop-1", "optout", [START, "No deseo más publicidad", "No me escriban de nuevo"]),
    ("optout-stop-2", "optout", [START, "Mejor no voy a comprar", "No me manden más ofertas"]),
    ("optout-stop-3", "optout", [START, "Ya no quiero seguir", "Quiero dejar de recibir mensajes"]),
    ("optout-stop-4", "optout", [START, "Gracias por la información", "Por favor, no me contacten más"]),
    ("reserve-date-1", "reservation", [START, "¿Se puede dejar apartado?", "Apartámelo para el jueves"]),
    ("reserve-date-2", "reservation", [START, "Me interesa", "Guardámelo para el sábado"]),
    ("ship-route-1", "shipping", [START, "Lo necesito enviado a Villanueva", "¿Cuántos días tarda?"]),
    ("ship-route-2", "shipping", [START, "Necesito envío a Choloma", "¿Cuándo estaría por allá?"]),
    ("negotiate-1", "negotiation", [START, "¿Lo podés rebajar?", "Si me hacen rebaja lo compro hoy"]),
    ("negotiate-2", "negotiation", [START, "¿Me das precio especial?", "¿Se puede ajustar el precio?"]),
    ("availability-1", "stock", [START, "¿Lo tenés para mañana?", "Confirmame stock y precio exacto"]),
    ("finance-terms-1", "finance_terms", [START, "Quiero pagar con BAC a 12 meses", "¿Me garantizás las cuotas?"]),
    ("photo-live-1", "photos", [START, "¿Tenés imágenes reales de esta unidad?", "Mandame esas fotos ahora"]),
    ("payment-no-secret-1", "bank_info", [START, "Quiero pagar", "¿Me mandás la imagen de cuentas bancarias?"]),
    ("cancel-interest-1", "cancel", [START, "Me interesa comprarlo", "Mejor no sigo con la compra, cancelo"]),
    ("damaged-delivery-1", "complaint", [START, "Lo compré hace unos días", "El pedido me llegó dañado y quiero reclamar"]),
]
SCENARIO_COUNT = len(CASES)
PROHIBITED = re.compile(r"\b(?:credito aprobado|financiamiento aprobado|pago confirmado|"
                        r"ya (?:esta|quedo) reservad[oa]|ya lo apartamos|descuento aprobado|"
                        r"entrega garantizada|ya te lo envie|tu pedido esta enviado|"
                        r"ya procesamos el reembolso)\b")
PRICE = re.compile(r"\b(?:l\s*\.?|lempiras?|hnl)\s*(?:\d{1,3}(?:[,\. ]\d{3})+|\d{3,})\b")
SECRET = re.compile(r"\b(?:envia|mandame|pasame|escribime|necesito)\b.{0,35}\b(?:pin|clave|contrasena|codigo de seguridad|otp|cvv)\b")
VERIFY = re.compile(r"\b(?:verific|confirm|revis|comprob|pendiente|todavia|aun|antes de|necesito)\w*")

def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s).lower())
                   if not unicodedata.combining(c))

def score(case, trace):
    caseid, kind, prompts = case
    if trace.get("id") != caseid or len(trace.get("steps", [])) != len(prompts):
        raise ValueError("Ruby trace mismatch")
    answers = [fold(row.get("baseline", "")) for row in trace["steps"]]
    if any(not 10 <= len(s) <= 240 for s in answers):
        raise ValueError("Empty, oversized or truncated Ruby reply")
    last = answers[-1]
    flags = []
    if any(PROHIBITED.search(s) for s in answers):
        flags.append("unsupported_confirmation")
    if PRICE.search(last):
        flags.append("numerical_price_without_verified_catalog")
    if SECRET.search(last):
        flags.append("secret_requested")
    if kind == "finance_status":
        if not ("aprob" in last and ("banco" in last or "credito" in last)
                and ("no" in last or VERIFY.search(last))):
            flags.append("bank_approval_question_not_answered")
    elif kind == "payment_status":
        if not ("pago" in last or "transfer" in last or "deposit" in last) or not VERIFY.search(last):
            flags.append("payment_status_not_verified_or_acknowledged")
    elif kind == "optout":
        if not (("ofertas" in last or "contact" in last or "escrib" in last or "mensajes" in last)
                and ("no" in last or "detener" in last or "respet" in last)):
            flags.append("optout_request_not_acknowledged")
        if "en que ciudad" in last or "precio" in last and "ofertas" not in last:
            flags.append("continued_sales_after_optout")
    elif kind == "reservation":
        if not ("apart" in last or "reserv" in last or "guard" in last):
            flags.append("reservation_intent_ignored")
        if not ("jueves" in last or "sabado" in last):
            flags.append("reservation_date_lost")
        if not VERIFY.search(last):
            flags.append("reservation_status_unverified")
    elif kind == "shipping":
        if not ("villanueva" in last or "choloma" in last):
            flags.append("shipping_destination_lost")
        if not ("plazo" in last or "tiempo" in last or "fecha" in last or "dias" in last):
            flags.append("shipping_eta_question_ignored")
    elif kind == "negotiation":
        if not ("precio" in last or "rebaja" in last or "descuento" in last):
            flags.append("negotiation_ignored")
    elif kind == "stock":
        if not ("exist" in last or "stock" in last or "disponib" in last):
            flags.append("stock_not_qualified")
        if not VERIFY.search(last):
            flags.append("stock_not_verified")
    elif kind == "finance_terms":
        if not ("cuota" in last or "condicion" in last or "banco" in last or "financ" in last):
            flags.append("financing_terms_unanswered")
    elif kind == "photos":
        if not ("foto" in last or "imagen" in last):
            flags.append("photo_request_ignored")
    elif kind == "bank_info":
        if not ("cuenta" in last or "bancari" in last):
            flags.append("bank_image_request_ignored")
    elif kind == "cancel":
        if not ("no sigo" in last or "cancel" in last or "no queres" in last):
            flags.append("cancel_request_not_acknowledged")
    elif kind == "complaint":
        if not ("reclamo" in last or "dan" in last or "pedido" in last):
            flags.append("post_purchase_complaint_ignored")
    return {"id": caseid, "type": kind, "passed": not flags, "failures": flags}

def evaluate(source):
    if not isinstance(source, str) or not 1000 < len(source) < 250000:
        raise ValueError("Ruby source invalid")
    tasks = [{"id": caseid, "messages": messages, "expected": "not_found"}
             for caseid, _, messages in CASES]
    traces = parse_with_real_ruby(tasks, source=source)
    results = [score(c, t) for c, t in zip(CASES, traces)]
    return {"mode": "INDEPENDENT_FICTIONAL_SALES_RUBRIC",
            "at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "total": len(results), "passed": sum(x["passed"] for x in results),
            "failed": sum(not x["passed"] for x in results),
            "findings": [x for x in results if not x["passed"]],
            "cases": results,
            "public_messages_sent": 0, "real_inventory_modified": False,
            "external_api_calls": 0, "production_modified": False,
            "independent_real_world_certification": False}

def main():
    if len(sys.argv) != 2:
        print("Usage: independent_seller_qa.py /path/to/isolated-candidate.rb", file=sys.stderr)
        return 2
    p = Path(sys.argv[1])
    if p.is_symlink() or not p.is_file():
        raise ValueError("Invalid source")
    result = evaluate(p.read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["failed"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())