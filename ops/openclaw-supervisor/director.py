#!/usr/bin/env python3
"""SoftMobile director: deterministic, read-only multi-domain task coordinator.

Consumes ONLY the sanitized supervisor snapshot and bounded SQL aggregates.
Prepares proposals for OpenClaw specialists; never sends, buys, edits business
records, activates plugins, deploys, or changes customer-facing systems.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from supervisor import OUT, save

SCHEMA = 1
MAX_AGE_SECONDS = 5400
DIRECTOR_FILE = "DIRECTOR.json"
AREAS = ("ventas", "inventario", "operaciones", "finanzas",
         "calidad", "infraestructura", "publicidad", "desarrollo")
# Only the sales funnel and its internal safeguards are in scope.
# Repair workflows, staff productivity, WAHA transport and public deployment
# remain deferred. These IDs are exact and never authorize external actions.
SALES_TASK_IDS=frozenset((
    "ventas_simulaciones","ventas_seguimiento","ventas_calidad_conversacional",
    "ventas_autofix_review","ventas_catalogo_calidad",
    "inventario_sin_stock",
    "finanzas_no_conciliadas","operaciones_fotos","calidad_convergencia",
    "calidad_replay_aislado","publicidad_sin_fuente","desarrollo_pr",
    "infraestructura_recursos"
))

SQL = r"""
BEGIN TRANSACTION READ ONLY;
SELECT 'SM_DIRECTOR_DB=' || json_build_object(
  'orders_completed',(SELECT count(*) FROM orders WHERE completed_at IS NOT NULL),
  'orders_validated',(SELECT count(*) FROM orders WHERE validada_at IS NOT NULL),
  'daily_closes',(SELECT count(*) FROM location_daily_closes),
  'stock_transfers',(SELECT count(*) FROM stock_transfers),
  'transfers_by_state',(SELECT coalesce(json_object_agg(estado,n), '{}'::json)
    FROM (SELECT coalesce(estado,'unknown') estado,count(*) n
          FROM stock_transfers GROUP BY 1) s),
  'photo_requests_inventory_db',(SELECT count(*) FROM photo_requests),
  'training_queue',(SELECT count(*) FROM training_queue),
  'locations',(SELECT count(*) FROM locations)
)::text;
COMMIT;
"""

class Reject(Exception):
    """Unsafe, stale, missing or incompatible input."""

def verify_snapshot(data, now=None):
    if not isinstance(data, dict):
        raise Reject("missing supervisor snapshot")
    if data.get("mode") != "read_only" or data.get("production_changed") is not False:
        raise Reject("supervisor side-effect guard")
    if data.get("public_messages_sent") != 0:
        raise Reject("public send detected")
    if data.get("chatwoot", {}).get("coverage_complete") is not True:
        raise Reject("Chatwoot coverage incomplete")
    if data.get("chatwoot", {}).get("redacted") is not True:
        raise Reject("unredacted report")
    if data.get("release_gates",{}).get("public_messaging_ready") is not False:
        raise Reject("unapproved messaging gate")
    try:
        captured = datetime.fromisoformat(data["captured_utc"].replace("Z","+00:00"))
        now = now or datetime.now(timezone.utc)
        age=(now-captured).total_seconds()
        if not 0 <= age <= MAX_AGE_SECONDS:
            raise Reject("supervisor snapshot stale or future")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise Reject("invalid timestamp") from exc
    return age

def db_snapshot():
    result=subprocess.run(
        ["runuser","-u","postgres","--","psql","-X","-At","-v","ON_ERROR_STOP=1","-d","inventory_db"],
        input=SQL,check=False,capture_output=True,text=True,timeout=20)
    if result.returncode:
        raise Reject("inventory SQL unavailable")
    raw=next((line[len("SM_DIRECTOR_DB="):] for line in result.stdout.splitlines()
              if line.startswith("SM_DIRECTOR_DB=")),None)
    if not raw:
        raise Reject("inventory SQL missing output")
    data=json.loads(raw)
    for k in ("orders_completed","orders_validated","daily_closes",
              "stock_transfers","photo_requests_inventory_db",
              "training_queue","locations"):
        if type(data.get(k)) is not int or data[k]<0:
            raise Reject("inventory aggregate invalid")
    states=data.get("transfers_by_state")
    if not isinstance(states,dict) or any(
        not isinstance(k,str) or type(v) is not int or v<0 for k,v in states.items()):
        raise Reject("invalid transfer states")
    return data

def task(id,area,priority,title,action,evidence=None,status="review",owner="humano"):
    assert area in AREAS
    assert priority in ("alta","media","baja")
    assert status in ("review","blocked")
    assert id.replace("_","").isalnum()
    return {"id":id,"area":area,"priority":priority,"title":title,
            "next_action":action,"evidence":evidence or {},
            "status":status,"owner":owner,"requires_approval":True,
            "automatic_external_actions":0}

def synthetic_qa_snapshot():
    """Read summaries of isolated, entirely fictional QA; never raw dialogues."""
    folder=Path("/opt/softmobile-waha-test/laboratorio-ia/quality")
    try:
        triage=json.loads((folder/"issue-triage-report.json").read_text())
        replay=json.loads((folder/"offline-issue-replay-report.json").read_text())
        t=datetime.fromisoformat(replay["at"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-t).total_seconds()
        if not 0<=age<=86400*2:
            return {"available":False,"reason":"stale"}
        if (replay.get("environment")!="NO_NETWORK_SYNTHETIC_ONLY" or
            replay.get("api_calls")!=0 or replay.get("public_messages_sent")!=0 or
            replay.get("real_inventory_changed") is not False or
            replay.get("no_auto_promotion") is not True):
            return {"available":False,"reason":"safety_guard"}
        if type(triage.get("total_records")) is not int or type(replay.get("replayed")) is not int:
            return {"available":False,"reason":"invalid_counts"}
        outcomes=replay.get("outcomes")
        if not isinstance(outcomes,dict) or any(
            type(v) is not int or v<0 for v in outcomes.values()):
            return {"available":False,"reason":"invalid_outcomes"}
        if sum(outcomes.values())!=replay["replayed"]:
            return {"available":False,"reason":"inconsistent_outcomes"}
        return {"available":True,"synthetic_issues":triage["total_records"],
            "replayed":replay["replayed"],"outcomes":outcomes,
            "synthetic_only":True,"auto_promotion":False}
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return {"available":False,"reason":"unavailable"}

def sales_simulation_snapshot():
    """Only synthetic sales funnel totals, never buyer dialogue text or mocks."""
    path=Path("/opt/softmobile-waha-test/laboratorio-ia/quality/sales-conversion-training-report.json")
    try:
        report=json.loads(path.read_text())
        at=datetime.fromisoformat(report["at"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-at).total_seconds()
        if not 0<=age<=86400:
            return {"available":False,"reason":"stale"}
        if (report.get("environment")!="OFFLINE_TRAINING_ONLY" or
            report.get("public_messages_sent")!=0 or
            report.get("real_orders")!=0 or
            report.get("real_inventory_modified") is not False):
            return {"available":False,"reason":"safety_guard"}
        # Never claim simulations passed for a different Ruby bot version.
        live=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
        sha=hashlib.sha256(live.read_bytes()).hexdigest()
        if (report.get("is_live_source") is not True or
            report.get("scored_source_sha256")!=sha):
            return {"available":False,"reason":"source_drift"}
        cases=report.get("scenarios")
        passed=report.get("passed")
        failed=report.get("failed")
        if (any(type(x) is not int for x in (cases,passed,failed)) or
            not 0<cases<=1000 or not 0<=passed<=cases or failed!=cases-passed):
            return {"available":False,"reason":"invalid_counts"}
        families=report.get("by_family")
        if not isinstance(families,dict) or not families:
            return {"available":False,"reason":"invalid_families"}
        if any(not isinstance(k,str) or not isinstance(v,dict) or
               type(v.get("passed")) is not int or type(v.get("tested")) is not int
               or not 0<=v["passed"]<=v["tested"] for k,v in families.items()):
            return {"available":False,"reason":"invalid_family_totals"}
        if sum(v["tested"] for v in families.values())!=cases:
            return {"available":False,"reason":"inconsistent_families"}
        return {"available":True,"scenarios":cases,"passed":passed,
                "failed":failed,"by_family":families,"synthetic_only":True,
                "real_checkouts":0,"public_messages_sent":0}
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return {"available":False,"reason":"unavailable"}

def seller_quality_snapshot():
    """Independent, actual Ruby reply scoring vs deterministic buyer expectations.

    Reports only counts from the fully fictional and network-disabled sales lab.
    The older simulated-checkout success rate cannot replace this result.
    """
    path=Path("/opt/softmobile-waha-test/laboratorio-ia/quality/seller-conversation-baseline.json")
    try:
        report=json.loads(path.read_text())
        at=datetime.fromisoformat(report["at"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-at).total_seconds()
        if not 0<=age<=86400:
            return {"available":False,"reason":"stale"}
        sha=hashlib.sha256(
            Path("/opt/softmobile-waha-test/sales-bot-v2.rb").read_bytes()).hexdigest()
        if (report.get("environment")!="OFFLINE_RUBY_SELLER_QA_ONLY" or
            report.get("candidate") is not False or
            report.get("source_sha256")!=sha or
            report.get("public_messages_sent")!=0 or
            report.get("real_sales")!=0 or
            report.get("api_calls")!=0 or
            report.get("production_modified") is not False or
            report.get("inventory_modified") is not False or
            report.get("auto_deploy_permitted") is not False):
            return {"available":False,"reason":"safety_guard_or_source_drift"}
        tested,passed,failed=(report.get(k) for k in ("scenarios","passed","failed"))
        families=report.get("by_family")
        if (any(type(x) is not int for x in (tested,passed,failed)) or
            tested!=72 or not 0<=passed<=tested or failed!=tested-passed or
            not isinstance(families,dict) or len(families)!=6 or
            any(type(v.get("tested")) is not int or
                type(v.get("passed")) is not int or
                v["tested"]!=12 or not 0<=v["passed"]<=v["tested"]
                for v in families.values()) or
            sum(v["passed"] for v in families.values())!=passed):
            return {"available":False,"reason":"invalid_counts"}
        return {"available":True,"scenarios":tested,"passed":passed,
                "failed":failed,"by_family":families,
                "synthetic_only":True,"real_sales":0,
                "ruby_source_sha256":sha}
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return {"available":False,"reason":"unavailable"}

def autonomous_sales_snapshot():
    """Only proven candidate metadata, no source code or customer data."""
    base=Path("/opt/softmobile-waha-test/laboratorio-ia/quality/autonomous-sales")
    try:
        data=json.loads((base/"latest.json").read_text())
        at=datetime.fromisoformat(data["completed_at"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-at).total_seconds()
        if not 0<=age<=86400:
            return {"available":False,"reason":"stale"}
        sha=hashlib.sha256(Path("/opt/softmobile-waha-test/sales-bot-v2.rb").read_bytes()).hexdigest()
        if (data.get("environment")!="OFFLINE_AUTONOMOUS_SALES" or
            data.get("scope")!="sales_only" or
            data.get("source_sha256")!=sha or
            data.get("source_pinned") is not True or
            data.get("candidate_deployed") is not False or
            data.get("candidate_integrated") is not False or
            data.get("deployment_authorized") is not False or
            data.get("public_messages_sent")!=0 or
            data.get("real_sales")!=0 or
            data.get("payments_initiated")!=0 or
            data.get("real_inventory_modified") is not False):
            return {"available":False,"reason":"unsafe_or_source_drift"}
        item=data.get("winning_candidate") or {}
        result=data.get("evaluations") or []
        if (data.get("status")!="qa_passed_review_required" or
            data.get("candidate_staged") is not True or
            not isinstance(result,list) or not 1<=len(result)<=3 or
            item.get("auto_deploy") is not False or
            type(data.get("challenge_count")) is not int or
            data["challenge_count"]!=6 or
            data.get("challenge_qa_passed") is not True):
            return {"available":False,"reason":"candidate_unverified"}
        qa=result[-1]
        if (qa.get("status")!="qa_passed_review_required" or
            qa.get("dialogue_passed")!=72 or qa.get("holdout_passed")!=18 or
            qa.get("legacy_checkout_passed")!=72 or
            type(qa.get("unit_tests_passed")) is not int or qa["unit_tests_passed"]<21 or
            qa.get("generated_challenges",{}).get("passed")!=6 or
            qa.get("adversarial_cases",{}).get("passed")!=11 or
            qa.get("adversarial_cases",{}).get("tested")!=11):
            return {"available":False,"reason":"QA_not_complete"}
        file=Path(item["candidate_file"])
        if (file.is_symlink() or file.parent!=base/"candidates" or
            not file.is_file() or
            hashlib.sha256(file.read_bytes()).hexdigest()!=item["sha256"]):
            return {"available":False,"reason":"untrusted_patch_artifact"}
        return {"available":True,"status":"qa_passed_review_required",
            "iterations":len(result),"candidate_sha256":item["sha256"],
            "source_sha256":sha,"candidate_dialogues_passed":72,
            "candidate_holdouts_passed":18,"candidate_rotating_passed":6,
            "candidate_synthetic_checkout_passed":72,
            "candidate_adversarial_passed":11,
            "candidate_unit_tests_passed":qa["unit_tests_passed"],
            "autonomous_failure_corrected":(
                data.get("auto_corrected_ever") is True or len(result)>1),
            "challenge_source":data["challenge_source"],
            "real_sales":0,"public_messages_sent":0,
            "candidate_deployed":False,"manual_review_required":True}
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return {"available":False,"reason":"unavailable"}

def attach_autonomous_sales(out,autofix):
    """New active internal sales review task; never changes production."""
    if out.get("scope")!="sales_only":
        raise Reject("autofix review must be sales scoped")
    out={**out,"autonomous_sales":autofix}
    if autofix.get("available") is not True:
        return out
    item=task("ventas_autofix_review","ventas","alta",
      "Candidato del vendedor automejorado en laboratorio y pendiente de revisión",
      "Revisar parche, pruebas independientes y autorización antes de cualquier integración.",
      {"candidate_sha256":autofix["candidate_sha256"],
       "source_sha256":autofix["source_sha256"],
       "dialogues_passed":autofix["candidate_dialogues_passed"],
       "rotating_passed":autofix["candidate_rotating_passed"],
       "adversarial_passed":autofix["candidate_adversarial_passed"],
       "unit_tests_passed":autofix["candidate_unit_tests_passed"],
       "candidate_deployed":False,"public_messages_sent":0,
       "requires_human_review":True})
    tasks=[*out["tasks"],item]
    return {**out,"tasks":tasks,
      "counts":{"all":len(tasks),
          "review":sum(t["status"]=="review" for t in tasks),
          "blocked":sum(t["status"]=="blocked" for t in tasks)},
      "specialists":{a:sum(t["area"]==a for t in tasks) for a in AREAS}}

def sales_catalog_snapshot():
    """Sanitized counts only; ERP record is never authoritative live quote."""
    path=OUT/"CATALOG_AUDIT.json"
    try:
        data=json.loads(path.read_text())
        stamp=datetime.fromisoformat(data["at"].replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-stamp).total_seconds()
        if not 0<=age<=7*3600:
            return {"available":False,"reason":"stale"}
        if (data.get("scope")!="sales_only" or
            data.get("mode")!="read_only_sales_catalog_aggregate" or
            data.get("source")!="ERP_database_internal_only" or
            data.get("public_messages_sent")!=0 or
            data.get("payments_initiated")!=0 or
            data.get("inventory_updated") is not False or
            data.get("customer_data_extracted") is not False or
            data.get("raw_price_or_cost_extracted") is not False or
            data.get("sku_or_serial_extracted") is not False or
            data.get("outbound_customer_quote_authorized") is not False or
            data.get("stock_freshness_verified") is not False or
            data.get("price_freshness_verified") is not False):
            return {"available":False,"reason":"unsafe"}
        c=data["counts"]
        wanted=("active_products","stocked_active_products",
          "stocked_fully_specified","active_price_below_cost",
          "active_without_stock","stocked_missing_required_quote_fields")
        if (any(type(c.get(k)) is not int or c[k]<0 for k in wanted) or
            c["stocked_active_products"]>c["active_products"] or
            c["stocked_fully_specified"]>c["stocked_active_products"] or
            c["active_without_stock"]!=c["active_products"]-c["stocked_active_products"] or
            c["stocked_missing_required_quote_fields"]!=
              c["stocked_active_products"]-c["stocked_fully_specified"]):
            return {"available":False,"reason":"invalid_aggregates"}
        return {"available":True,"active_products":c["active_products"],
          "stocked_active_products":c["stocked_active_products"],
          "stocked_fully_specified":c["stocked_fully_specified"],
          "active_price_below_cost":c["active_price_below_cost"],
          "active_without_stock":c["active_without_stock"],
          "stocked_missing_required_quote_fields":
              c["stocked_missing_required_quote_fields"],
          "public_quote_authorized":False,"fresh_partner_quote_available":False}
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return {"available":False,"reason":"unavailable"}

def attach_sales_catalog(out,catalog):
    if out.get("scope")!="sales_only":
        raise Reject("catalog requires sales-only director")
    out={**out,"sales_catalog":catalog}
    if catalog.get("available") is not True:
        return out
    item=task("ventas_catalogo_calidad","ventas","alta",
        "Revisar precios, calidad de catálogo y existencias sin prometer ventas",
        "Conciliar inventario por unidad y aliado; comprobar precio vigente y márgenes antes de cotizar. No alterar stock o precios automáticamente.",
        {"active_products":catalog["active_products"],
         "stocked_active_products":catalog["stocked_active_products"],
         "stocked_fully_specified":catalog["stocked_fully_specified"],
         "active_without_stock":catalog["active_without_stock"],
         "active_price_below_cost":catalog["active_price_below_cost"],
         "public_quote_authorized":False,
         "fresh_partner_quote_available":False})
    tasks=[*out["tasks"],item]
    return {**out,"tasks":tasks,
      "counts":{"all":len(tasks),
                "review":sum(t["status"]=="review" for t in tasks),
                "blocked":sum(t["status"]=="blocked" for t in tasks)},
      "specialists":{a:sum(t["area"]==a for t in tasks) for a in AREAS}}

def plan(data,metrics=None,qa=None,conversion=None,seller_quality=None):
    """Pure orchestration: no input is modified and no external API is called."""
    verify_snapshot(data)
    metrics=metrics or {}
    qa=qa or {}
    conversion=conversion or {}
    seller_quality=seller_quality or {}
    chat=data["chatwoot"]
    q=chat.get("queues") or {}
    fw=data.get("followups") or {}
    quality=data.get("quality") or {}
    inv=data.get("inventory") or {}
    photo=data.get("photos") or {}
    health=data.get("health") or {}
    ready=data.get("release_gates") or {}
    tasks=[]
    if q.get("unanswered"):
        tasks.append(task("ventas_respuestas","ventas","alta",
            "Conversaciones del buzón piloto sin respuesta",
            "Revisar las conversaciones en Chatwoot y distinguir pruebas de clientes reales.",
            {"conversation_ids":sorted(set(q["unanswered"]))}))
    if fw.get("cases"):
        tasks.append(task("ventas_seguimiento","ventas","alta",
            "Oportunidades de seguimiento de cotizaciones",
            "Verificar autorización, respuesta humana y canal antes de cualquier contacto.",
            {"cases":fw["cases"]}))
    if conversion.get("available") is True:
        failures=conversion["failed"]
        tasks.append(task("ventas_simulaciones","ventas",
            "alta" if failures else "media",
            "Simulaciones de compra y cierre con inventario ficticio",
            "Investigar regresiones antes de liberar WhatsApp; resultados ficticios nunca autorizan un lanzamiento.",
            {"scenarios":conversion["scenarios"],"passed":conversion["passed"],
             "failed":failures,"synthetic_only":True}))
    if seller_quality.get("available") is True:
        total=seller_quality["scenarios"]
        failed=seller_quality["failed"]
        passed=seller_quality["passed"]
        tasks.append(task("ventas_calidad_conversacional","ventas",
            "alta" if failed else "media",
            "Respuestas comerciales del vendedor Ruby verificadas en conversaciones completas",
            "Revisar y comparar en rama las respuestas sobre objeciones, reservas, envío y cierres. Un checkout sintético no demuestra atención ni ventas reales.",
            {"scenarios":total,"passed":passed,"failed":failed,
             "by_family":seller_quality["by_family"],
             "ruby_source_sha256":seller_quality["ruby_source_sha256"],
             "synthetic_only":True,"verified_real_sales":0}))
    if not ready.get("public_messaging_ready",False):
        tasks.append(task("ventas_despliegue","ventas","alta",
            "Vendedor y seguimiento público no liberados",
            "Validar transporte, QA independiente y consentimiento antes de solicitar habilitación.",
            {"blockers":ready.get("blockers",[])},"blocked"))
    if inv.get("status")=="ok":
        missing=inv.get("out_of_stock_active_products",0)
        if missing>0:
            tasks.append(task("inventario_sin_stock","inventario","alta",
                "Productos activos sin unidades disponibles",
                "Priorizar revisión de catálogo y abastecimiento; no comprar ni alterar stock.",
                {"active_products_without_stock":missing,
                 "available_units":inv.get("available_units")}))
        pending=inv.get("orders_pending",0)
        if pending and metrics.get("orders_completed")==0:
            tasks.append(task("finanzas_no_conciliadas","finanzas","alta",
                "No hay ventas completadas verificables",
                "Conciliar órdenes reales vs datos de prueba; no atribuir ingresos ni utilidades.",
                {"pending_order_records":pending,
                 "completed_orders":metrics.get("orders_completed"),
                 "daily_closes":metrics.get("daily_closes")}))
    if metrics.get("stock_transfers",0):
        tasks.append(task("inventario_transferencias","inventario","media",
            "Conciliar estados de transferencias",
            "Auditar significado de estados; no interpretar 'confirmada' como pendiente o finalizada sin reglas.",
            {"total_transfers":metrics["stock_transfers"],
             "states":metrics["transfers_by_state"]}))
    pending_photo=photo.get("older_than_2h_pending_review_ids") or []
    if pending_photo:
        tasks.append(task("operaciones_fotos","operaciones","alta",
            "Solicitudes de fotografías antiguas",
            "Comprobar cuáles son pruebas y asignar revisión humana sin contactar al cliente.",
            {"request_ids":pending_photo}))
    tasks.append(task("operaciones_reparaciones","operaciones","media",
        "Sin fuente de órdenes de reparación confirmada",
        "Conectar el módulo de reparaciones con esquema y permisos de solo lectura.",
        {"source":"not_found_in_inventory_db"},"blocked"))
    tasks.append(task("operaciones_empleados","operaciones","baja",
        "Métricas de empleados sin validación",
        "Definir turnos y asignación antes de medir productividad individual.",
        {"source":"not_configured"},"blocked"))
    if quality.get("independent_convergence") is not True:
        tasks.append(task("calidad_convergencia","calidad","alta",
            "QA sin convergencia independiente",
            "Repetir simulación, evaluación independiente y regresión antes de habilitar ventas públicas.",
            {"local_tests":quality.get("tests"),"local_passed":quality.get("all_local_tests_passed")}))
    if qa.get("available") is True and qa.get("replayed",0)>0:
        tasks.append(task("calidad_replay_aislado","calidad","alta",
            "Incidencias sintéticas reproducidas en laboratorio aislado",
            "Priorizar investigación y correcciones en rama; los indicadores son hipótesis, no defectos reales demostrados.",
            {"synthetic_replayed":qa["replayed"],"outcomes":qa["outcomes"]}))
    if not health.get("whatsapp_online"):
        tasks.append(task("infraestructura_waha_piloto","infraestructura","media",
            "WAHA de pruebas detenido",
            "Verificar uso efectivo del piloto antes de reiniciar; no concluir caída del WhatsApp de producción.",
            {"source":"softmobile-waha-test"}))
    if health.get("all_containers_running") is False:
        tasks.append(task("infraestructura_servicios","infraestructura","alta",
            "Servicio principal detenido",
            "Inspeccionar logs, memoria y dependencias; proponer recuperación controlada."))
    if float(health.get("disk_free_percent",100))<15 or float(health.get("memory_available_percent",100))<10:
        tasks.append(task("infraestructura_recursos","infraestructura","alta",
            "Recursos VPS bajos","Diagnosticar sin borrar datos ni reiniciar servicios.",
            {"disk_free_percent":health.get("disk_free_percent"),
             "memory_available_percent":health.get("memory_available_percent")}))
    tasks.append(task("publicidad_sin_fuente","publicidad","media",
        "Faltan métricas verificadas de Meta Ads",
        "Conectar fuente autorizada de gasto, conversaciones atribuibles y conversiones; no tocar campañas.",
        {"source":"not_connected_to_supervisor"},"blocked"))
    tasks.append(task("desarrollo_pr","desarrollo","media",
        "Mantener cambios auditables en GitHub",
        "Preparar cambios sobre rama con pruebas y PR en borrador; no desplegar sin QA.",
        {"pull_request":156}))
    order={"alta":0,"media":1,"baja":2}
    tasks=sorted(tasks,key=lambda t:(order[t["priority"]],t["area"],t["id"]))[:30]
    return {"schema_version":SCHEMA,"mode":"proposals_only","public_messages_sent":0,
            "production_changed":False,"source_utc":data["captured_utc"],
            "tasks":tasks,
            "counts":{"all":len(tasks),
                      "review":sum(t["status"]=="review" for t in tasks),
                      "blocked":sum(t["status"]=="blocked" for t in tasks)},
            "specialists":{a:sum(t["area"]==a for t in tasks) for a in AREAS},
            "synthetic_qa":qa if qa.get("available") is True else {"available":False},
            "synthetic_sales":conversion if conversion.get("available") is True else {"available":False},
            "seller_reply_quality":seller_quality if seller_quality.get("available") is True else {"available":False},
            "verified_finance":{"completed_orders":metrics.get("orders_completed"),
                                "daily_closes":metrics.get("daily_closes"),
                                "profit_verified":False}}

def sales_focus(out):
    """Restrict the live director to commercial tasks; retain zero external actions.

    Historical general-purpose plan() remains available for offline tests only.
    Nothing queued about repairs, employees, WAHA transport or public launch.
    """
    if (out.get("mode")!="proposals_only" or
        out.get("public_messages_sent")!=0 or
        out.get("production_changed") is not False):
        raise Reject("unsafe focus source")
    tasks=[t for t in out["tasks"] if t["id"] in SALES_TASK_IDS]
    if not all(t.get("requires_approval") is True and
               t.get("automatic_external_actions")==0 for t in tasks):
        raise Reject("unsafe sales tasks")
    return {**out,"scope":"sales_only","deferred_features":[
        "repairs","employee_analytics","whatsapp_transport","public_release"],
        "tasks":tasks,
        "counts":{"all":len(tasks),
                  "review":sum(t["status"]=="review" for t in tasks),
                  "blocked":sum(t["status"]=="blocked" for t in tasks)},
        "specialists":{a:sum(t["area"]==a for t in tasks) for a in AREAS}}

def markdown(out):
    rows=["# OpenClaw — Director de ventas SoftMobile",
      "Modo de solo lectura. Solo ventas y soporte comercial (sin reparaciones ni WhatsApp).",
      "Todas las acciones son PROPUESTAS sujetas a aprobación.",
      "Fuente UTC: "+out["source_utc"],
      "Tareas: "+str(out["counts"]["all"])+
      " | Para revisión: "+str(out["counts"]["review"])+
      " | Bloqueadas por integración/seguridad: "+str(out["counts"]["blocked"]),
      "Mensajes a clientes: 0; compras: 0; campañas modificadas: 0; despliegues: 0.",
      "Ganancia confirmada: no verificable con los registros actuales.",
      "QA aislado: "+str(out.get("synthetic_qa",{}).get("replayed","sin dato"))+
      " conversaciones ficticias; resultados no prueban defectos reales.",
      "Embudo comercial ficticio: "+str(out.get("synthetic_sales",{}).get("passed","?"))+
      "/"+str(out.get("synthetic_sales",{}).get("scenarios","?"))+
      " simulaciones; no hay ventas reales confirmadas.",
      "Calidad conversacional del Ruby actual: "+
      str(out.get("seller_reply_quality",{}).get("passed","?"))+"/"+
      str(out.get("seller_reply_quality",{}).get("scenarios","?"))+
      " escenarios. No equivale a cierre de ventas reales.",
      "", "## Cola por especialidad"]
    for t in out["tasks"]:
        rows.append("- ["+t["priority"]+" / "+t["status"]+"] "+
            t["area"]+": "+t["title"]+" — "+t["next_action"])
    rows.extend(["","Las tareas con datos de prueba no deben tratarse como ventas o solicitudes reales.",
                 "Consultar DIRECTOR.json para evidencia estructurada; sin PII.", ""])
    return "\n".join(rows)

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        data=json.loads((OUT/"latest.json").read_text())
        verify_snapshot(data)
    except (OSError,ValueError,Reject) as exc:
        print("Rejected input:",type(exc).__name__)
        return 2
    try:
        metrics=db_snapshot()
    except (OSError,ValueError,Reject,subprocess.TimeoutExpired):
        metrics={"read_only_data_available":False}
    qa=synthetic_qa_snapshot()
    conversion=sales_simulation_snapshot()
    seller=seller_quality_snapshot()
    out=attach_sales_catalog(
        attach_autonomous_sales(
            sales_focus(plan(data,metrics,qa,conversion,seller_quality=seller)),
            autonomous_sales_snapshot()),
        sales_catalog_snapshot())
    save(OUT/DIRECTOR_FILE,json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"DIRECTOR.md",markdown(out))
    print(json.dumps({"tasks":out["counts"],"specialists":out["specialists"],
          "public_messages_sent":0,"finance_data":bool(metrics.get("orders_completed") is not None)},
          ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
