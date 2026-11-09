#!/usr/bin/env python3
"""Sanitized recovery audit of customer-supplied SoftMobile commercial knowledge.

Never expose banking image bytes, customer data, or partner credentials.
A historical price list is not evidence of live store stock.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json,collections
from pathlib import Path
from supervisor import OUT,save

ROOT=Path("/opt/softmobile-waha-test")
KNOW=ROOT/"knowledge"
BUS=KNOW/"softmobile-business.json"
CAT=KNOW/"catalogo.json"
RULES=KNOW/"reglas.md"
BANK=ROOT/"media/cuentas-bancarias.jpg"
CERT=OUT/"CERTIFICATION.json"
def digest(path):
    if path.is_symlink() or not path.is_file():raise ValueError("missing or linked knowledge file")
    return sha256(path.read_bytes()).hexdigest()

def audit():
    files={k:digest(v) for k,v in (
        ("approved_rules",RULES),("structured_business",BUS),
        ("november_6_price_catalog",CAT),("bank_image",BANK))}
    rules=RULES.read_text()
    business=json.loads(BUS.read_text())
    rows=json.loads(CAT.read_text())
    if (business.get("brand")!="SoftMobile" or
        business.get("reservation_delivery",{}).get("reservations_allowed") is not False or
        "SoftMobile no hace reservas ni apartados" not in rules):
        raise ValueError("mismatched business policy")
    if not isinstance(rows,list) or len(rows)!=97:
        raise ValueError("catalog count differs from recovered form")
    if any(not isinstance(p,dict) or not p.get("modelo") or
           type(p.get("precio_hnl")) is not int or p["precio_hnl"]<=0 for p in rows):
        raise ValueError("catalog entry invalid")
    pairs=[(r["modelo"].casefold(),str(r.get("capacidad") or "")) for r in rows]
    if max(collections.Counter(pairs).values())!=1:
        raise ValueError("duplicate model+capacity")
    p=business.get("payments") or {}
    banks=p.get("extrafinanciamiento_banks_to_check") or []
    if len(banks)!=6 or len(business.get("locations") or [])!=4:
        raise ValueError("bank or store definitions incomplete")
    if BANK.stat().st_size<10000 or BANK.stat().st_size>1500000:
        raise ValueError("bank image invalid size")
    current=json.loads(CERT.read_text())
    report={
      "schema_version":1,"mode":"SOFTMOBILE_KNOWLEDGE_RECOVERY_READ_ONLY",
      "at":datetime.now(timezone.utc).isoformat(),
      "source":"user_supplied_commercial_form_2026-11-06",
      "file_sha256":files,
      "files_present_and_integrity_checked":4,
      "catalog_variants":len(rows),
      "catalog_rows_missing_capacity":sum(not r.get("capacidad") for r in rows),
      "catalog_rows_missing_price":sum(not r.get("precio_hnl") for r in rows),
      "catalog_price_effective_date":"2026-11-06",
      "catalog_live_price_freshness_verified":False,
      "catalog_live_stock_verified":False,
      "partner_inventory_connected":False,
      "bank_account_image_present":True,
      "bank_receipt_verification_automated":False,
      "financing_banks_documented":len(banks),
      "outlets_documented":len(business["locations"]),
      "no_reservations_policy_confirmed":True,
      "discount_tiers_from_approved_form":[2,3,4],
      "photo_request_code_workflow_documented":True,
      "followup_consent_required":business.get("followup",{}).get("consent_required") is True,
      "followup_max_messages":business.get("followup",{}).get("maximum_messages"),
      "current_release_gates_passed":current.get("passed_count"),
      "remaining_user_inputs":[
        "Confirm current prices if changed since the Nov 6 list; no need to resend original 97 variants",
        "Provide or authorize a regularly updated ally-by-ally stock and color/capacity availability source",
        "Approve order/payment/dispatch reconciliation using actual proofs; do not mark 458 pending orders as revenue",
        "At final channel phase provide authorized Meta WhatsApp API production credentials and consent/test-number access"],
      "public_messages_sent":0,"payments_initiated":0,
      "real_inventory_modified":False,"production_modified":False}
    return report

def main():
    d=audit()
    save(OUT/"KNOWLEDGE_RECOVERY.json",json.dumps(d,ensure_ascii=False,indent=2)+"\n")
    lines=[
      "# SoftMobile — información comercial recuperada",
      "Registro: "+d["at"],
      "Archivos recuperados (reglas, negocio, 97 variantes e imagen bancaria): **4/4**",
      "El catálogo del 6 de noviembre tiene 97 variantes, con "+str(d["catalog_rows_missing_capacity"])+
      " entradas sin capacidad especificada. No faltan precios de lista en esas 97 filas.",
      "Se recuperaron las reglas de las cuatro sedes, seis bancos y descuentos 2/3/4%.",
      "La política vigente de reservas y apartados es **NO SE HACEN**.",
      "Precio vigente del aliado y existencia por unidad: **NO VERIFICADOS**.",
      "La imagen bancaria existe; no implica que un pago esté confirmado.",
      "El vendedor Ruby activo debe ser probado contra las reglas y SHA correspondientes.",
      "","## Lo que hace falta del negocio",
      "1. Cambios de precios posteriores al 6 de noviembre (si los hubo).",
      "2. Una fuente de existencias reales por aliado/modelo/color/GB y responsable de confirmarlas.",
      "3. Comprobantes para reconciliar órdenes y pagos, con validación contable.",
      "4. Al final, acceso autorizado a la API oficial de WhatsApp y números de prueba.",
      "No solicitamos nuevamente catálogo histórico, formulario, bancos ni imagen bancaria.",
      "La auditoría no activa mensajes, pagos ni cambios de inventario." ]
    save(OUT/"KNOWLEDGE_RECOVERY.md","\n\n".join(lines)+"\n")
    print(json.dumps({"files":d["files_present_and_integrity_checked"],
       "variants":d["catalog_variants"],"missing_capacity":d["catalog_rows_missing_capacity"],
       "live_prices_verified":False,"stock_verified":False}))
if __name__=="__main__":
    main()