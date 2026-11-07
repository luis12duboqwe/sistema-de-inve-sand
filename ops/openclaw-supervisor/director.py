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
import json
import subprocess

from supervisor import OUT, save

SCHEMA = 1
MAX_AGE_SECONDS = 5400
DIRECTOR_FILE = "DIRECTOR.json"
AREAS = ("ventas", "inventario", "operaciones", "finanzas",
         "calidad", "infraestructura", "publicidad", "desarrollo")
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

def plan(data,metrics=None,qa=None):
    """Pure orchestration: no input is modified and no external API is called."""
    verify_snapshot(data)
    metrics=metrics or {}
    qa=qa or {}
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
            "verified_finance":{"completed_orders":metrics.get("orders_completed"),
                                "daily_closes":metrics.get("daily_closes"),
                                "profit_verified":False}}

def markdown(out):
    rows=["# OpenClaw — Director de operaciones SoftMobile",
      "Modo de solo lectura. Todas las acciones son PROPUESTAS sujetas a aprobación.",
      "Fuente UTC: "+out["source_utc"],
      "Tareas: "+str(out["counts"]["all"])+
      " | Para revisión: "+str(out["counts"]["review"])+
      " | Bloqueadas por integración/seguridad: "+str(out["counts"]["blocked"]),
      "Mensajes a clientes: 0; compras: 0; campañas modificadas: 0; despliegues: 0.",
      "Ganancia confirmada: no verificable con los registros actuales.",
      "QA aislado: "+str(out.get("synthetic_qa",{}).get("replayed","sin dato"))+
      " conversaciones ficticias; resultados no prueban defectos reales.",
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
    out=plan(data,metrics,qa)
    save(OUT/DIRECTOR_FILE,json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"DIRECTOR.md",markdown(out))
    print(json.dumps({"tasks":out["counts"],"specialists":out["specialists"],
          "public_messages_sent":0,"finance_data":bool(metrics.get("orders_completed") is not None)},
          ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
