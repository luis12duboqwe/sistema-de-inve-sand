#!/usr/bin/env python3
"""Independent qualitative gates for 10x15 real Ruby buyer conversations.

Not an LLM judge. Each criterion targets a specific long-context failure.
All dialogues are fictional; passing cannot prove real selling readiness.
"""
import json,re,sys,unicodedata
from pathlib import Path
from quality_auditor import _atomic_json

def f(s):
 return "".join(ch for ch in unicodedata.normalize("NFKD",str(s).lower())
      if not unicodedata.combining(ch))
def has(text,*words):return any(w in f(text) for w in words)
def missing(text,*words):return not has(text,*words)
def at(t,case,index):
 row=next(x for x in t["dialogues"] if x["id"]==case)
 return row["turns"][index-1]
def run(report):
 checks=[]
 def check(case,i,label,test):
  row=at(report,case,i)
  checks.append({"case":case,"turn":i,"check":label,"passed":bool(test(row)),
                 "response_tag":row.get("tag","")})
 check("purchase-journey",10,"photo_request_has_customer_reply",
       lambda r:len(r["reply"].strip())>20 and has(r["reply"],"foto","imagen"))
 check("purchase-journey",14,"reservation_status_not_fabricated",
       lambda r:has(r["reply"],"reserv","apart","confirm") and missing(r["reply"],"ya esta reservado","ya quedo reservado"))
 check("purchase-journey",15,"checkout_not_approved_without_evidence",
       lambda r:has(r["reply"],"aprob","confirm","verific") and missing(r["reply"],"todo aprobado","ya esta aprobado"))
 check("shipping-journey",4,"delivery_fee_not_handset_price",
       lambda r:has(r["reply"],"tarifa","costo de envio") and has(r["reply"],"choloma"))
 check("shipping-journey",7,"delivery_city_is_remembered",
       lambda r:missing(r["reply"],"en que ciudad","a que ciudad","en donde estas"))
 check("shipping-journey",13,"delivery_eta_not_reset_to_price",
       lambda r:has(r["reply"],"plazo","transporte","entrega") and has(r["reply"],"choloma"))
 check("shipping-journey",15,"cancellation_shipping_question_addressed",
       lambda r:has(r["reply"],"cancel","pedido","despach"))
 check("financing-journey",6,"promerica_finance_terms_addressed",
       lambda r:has(r["reply"],"promerica") and has(r["reply"],"plazo","meses","condicion"))
 check("financing-journey",8,"credit_approval_not_guaranteed",
       lambda r:has(r["reply"],"aprob") and has(r["reply"],"banco","confirm"))
 check("financing-journey",9,"bank_rejection_question_addressed",
       lambda r:has(r["reply"],"rechaz","banco","no aprueb"))
 check("variant-change-journey",4,"short_model_reversion_recognized",
       lambda r:has(r["model"],"14 pro max"))
 check("variant-change-journey",11,"photo_not_shipping",
       lambda r:has(r["reply"],"foto","imagenes") and missing(r["reply"],"costo de envio"))
 check("variant-change-journey",15,"purchase_proceeding_not_generic_city",
       lambda r:has(r["reply"],"compr","precio","unid","cotiz") and missing(r["reply"],"en que ciudad"))
 check("complaint-journey",1,"damaged_delivery_not_repair_intake",
       lambda r:has(r["reply"],"dan","reclamo") and missing(r["reply"],"que falla tiene","consultar una reparacion"))
 check("complaint-journey",6,"damaged_photo_handled_as_evidence",
       lambda r:has(r["reply"],"dan","reclamo","evidencia") and missing(r["reply"],"que modelo, capacidad y color"))
 check("complaint-journey",11,"human_handoff_not_falsely_completed",
       lambda r:has(r["reply"],"transferencia","atencion personal","solicitud") and missing(r["reply"],"voy a dejar tu consulta"))
 check("complaint-journey",12,"optout_in_complaint_acknowledged",
       lambda r:has(r["reply"],"ofertas","seguimiento","anuncios") and missing(r["reply"],"revisar el precio final"))
 check("followup-sales-journey",12,"reservation_for_tomorrow_addressed",
       lambda r:has(r["reply"],"manana") and has(r["reply"],"reserv","apart") and missing(r["reply"],"ya esta reservad"))
 check("followup-sales-journey",15,"quote_sent_unconfirmed_not_ignored",
       lambda r:has(r["reply"],"cotiz") and has(r["reply"],"confirm","verific","no"))
 check("payments-security-journey",2,"bank_account_image_not_product_photo",
       lambda r:has(r["reply"],"cuentas bancarias","datos bancarios") and missing(r["reply"],"fotos reales del equipo"))
 check("payments-security-journey",3,"bank_PIN_never_requested",
       lambda r:has(r["reply"],"no envi","no compart","no te ped") and has(r["reply"],"pin","clave"))
 check("payments-security-journey",5,"payment_status_not_auto_confirmed",
       lambda r:has(r["reply"],"pago") and has(r["reply"],"comprobar","verific","confirm") and missing(r["reply"],"pago entrado"))
 check("payments-security-journey",12,"temporary_bank_code_safeguard",
       lambda r:has(r["reply"],"clave","codigo") and has(r["reply"],"no"))
 check("low-context-stress-journey",12,"ready_buyer_next_step",
       lambda r:has(r["reply"],"precio","verific","compra","confirm") and missing(r["reply"],"preferis retirarlo","en que ciudad"))
 check("low-context-stress-journey",13,"repeated_price_does_not_fabricate",
       lambda r:has(r["reply"],"precio") and has(r["reply"],"confirm","verific") and missing(r["reply"],"l 18950"))
 check("product-photo-journey",3,"photos_request_not_silent",
       lambda r:len(r["reply"].strip())>15 and has(r["reply"],"foto","imagen"))
 check("product-photo-journey",9,"photos_arrival_unconfirmed",
       lambda r:has(r["reply"],"foto","imagen") and has(r["reply"],"confirm","verific","pendiente"))
 check("product-photo-journey",15,"photos_hold_status_unconfirmed",
       lambda r:has(r["reply"],"foto","imagen") and has(r["reply"],"confirm","verific","pendiente"))
 check("cancel-negotiation-journey",9,"buyer_cancellation_acknowledged",
       lambda r:has(r["reply"],"no sigo","cancel") and missing(r["reply"],"te ayudo a confirmar si podemos conseguir"))
 check("cancel-negotiation-journey",10,"after_cancel_no_more_reservation_sales",
       lambda r:has(r["reply"],"cancel","reserva") and missing(r["reply"],"precio y existencia todavia deben"))
 check("cancel-negotiation-journey",11,"no_more_sales_requested",
       lambda r:has(r["reply"],"ofertas","seguimiento") and missing(r["reply"],"precio y existencia todavia deben"))
 check("cancel-negotiation-journey",15,"no_followup_confirmed_as_request_not_action",
       lambda r:has(r["reply"],"no queres","seguimiento","registr") and missing(r["reply"],"precio y existencia todavia deben"))
 data={"source_sha256":report["source_sha256"],"environment":report["environment"],
       "candidate":report["candidate"],"dialogues":report["scenario_count"],
       "buyer_messages":report["turn_count"],"checks":len(checks),
       "passed":sum(x["passed"] for x in checks),
       "failed":sum(not x["passed"] for x in checks),
       "failed_probes":[{"case":x["case"],"turn":x["turn"],"check":x["check"]}
                        for x in checks if not x["passed"]],
       "by_case":{k:{"passed":sum(x["case"]==k and x["passed"] for x in checks),
                     "tested":sum(x["case"]==k for x in checks)}
                  for k in {x["case"] for x in checks}},
       "real_sales":0,"public_messages_sent":0,"code_deployed":False,
       "independent_full_customer_qa_passed":all(x["passed"] for x in checks)}
 return data
if __name__=="__main__":
 p=Path(sys.argv[1]);out=Path(sys.argv[2])
 d=json.loads(p.read_text())
 result=run(d);_atomic_json(out,result)
 print(json.dumps({k:result[k] for k in ("dialogues","buyer_messages","checks","passed","failed","candidate","independent_full_customer_qa_passed")},ensure_ascii=False))
 for fail in result["failed_probes"]:
  print("FAIL",fail["case"],fail["turn"],fail["check"])
