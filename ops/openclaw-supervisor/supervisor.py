#!/usr/bin/env python3
"""Read-only SoftMobile supervisor: Chatwoot, sales queue, lab and VPS."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

ROOT=Path("/opt/openclaw-lab")
OUT=ROOT/"workspace/softmobile-supervisor"
LAB=ROOT/"results/lab-cycles"
CONTAINERS=["openclaw-lab","softmobile-chatwoot-rails-1","softmobile-chatwoot-sidekiq-1",
            "softmobile-chatwoot-redis-1","softmobile-chatwoot-postgres-1"]
WHATSAPP=["softmobile-waha-test-waha-1","softmobile-waha-test-redis-1"]
PREFIX="SM_SUPERVISOR_JSON="
# Fixed account/buzon, no incoming parameters and no DB mutations.
RAILS=r"""
require 'json'
now=Time.now.utc
scope=Conversation.where(account_id:2,inbox_id:2)
total=scope.count
raise 'scope too large for safe batch' if total>5000
counts={'unanswered'=>[],'recoverable'=>[],'consented_followup'=>[],'human_review'=>[]}
reviewed=0
open_count=0
recent_count=0
scope.find_each(batch_size:100) do |c|
  reviewed+=1
  open=c.status=='open'
  open_count+=1 if open
  recent_count+=1 if c.updated_at>=24.hours.ago
  msgs=c.messages.where(private:false,message_type:[:incoming,:outgoing]).order(id: :desc).limit(60).to_a
  latest=msgs.max_by(&:created_at)
  next unless open && latest && latest.created_at>=7.days.ago
  incoming=msgs.select {|m| m.message_type=='incoming'}
  outgoing=msgs.select {|m| m.message_type=='outgoing'}
  i=incoming.max_by(&:created_at)
  o=outgoing.max_by(&:created_at)
  attrs=c.custom_attributes || {}
  human=attrs['sm_human_takeover']==true
  consent=attrs['sm_followup_consent']==true
  opted=incoming.any? {|m| m.content.to_s.match?(/no (?:me )?(?:escrib|contact|avis)|no quiero seguimiento|dejame de escribir|déjame de escribir/i)}
  quote=outgoing.any? {|m| m.content_attributes.is_a?(Hash) && m.content_attributes['sm_quote'].to_s=='true'}
  price=outgoing.any? {|m| m.content.to_s.match?(/\b(?:L\.?\s*|HNL\s*)\d[\d.,]{2,}/i)}
  interest=incoming.any? {|m| m.content.to_s.match?(/precio|cuanto|cuánto|tiene[n]?|disponible|iphone|samsung|cotiza|comprar|financia/i)}
  waiting_seller=i && (!o || i.created_at>o.created_at) && (now-i.created_at).between?(900,604800)
  waiting_buyer=o && (!i || o.created_at>i.created_at) && (now-o.created_at).between?(7200,259200)
  candidate=waiting_buyer && (quote || price || interest) && !human && !opted
  counts['unanswered'] << c.id if waiting_seller && !human
  counts['recoverable'] << c.id if candidate
  counts['consented_followup'] << c.id if candidate && consent && !outgoing.any? {|m| m.sender_type=='User'} && !attrs['sm_followup_quote_id']
  counts['human_review'] << c.id if candidate && (!consent || outgoing.any? {|m| m.sender_type=='User'})
end
counts.each_value(&:sort!)
puts 'SM_SUPERVISOR_JSON='+{account_id:2,inbox_id:2,total_conversations:total,
  reviewed_conversations:reviewed,recent_24h:recent_count,open_conversations:open_count,
  coverage_complete:total==reviewed,queues:counts,redacted:true,public_messages_sent:0}.to_json
"""

def shell(args, **kw):
    return subprocess.run(args,text=True,capture_output=True,check=False,**kw)

def chatwoot():
    result=shell(["docker","exec","-i","softmobile-chatwoot-rails-1","sh","-lc",
                  "RAILS_ENV=production bundle exec rails runner -"],input=RAILS,timeout=100)
    if result.returncode:
        raise RuntimeError("Rails runner failed; details kept private")
    match=next((x[len(PREFIX):] for x in result.stdout.splitlines() if x.startswith(PREFIX)),None)
    if not match:
        raise RuntimeError("No structured Chatwoot data")
    data=json.loads(match)
    if not (data.get("account_id")==2 and data.get("inbox_id")==2 and
            data.get("redacted") is True and data.get("coverage_complete") is True and
            data.get("public_messages_sent")==0):
        raise ValueError("Chatwoot scope, coverage or privacy violation")
    data["status"]="ok"
    return data

def lab():
    paths=sorted(LAB.glob("*-status.json"))
    if not paths:
        return {"available":False,"all_local_tests_passed":False}
    data=json.loads(paths[-1].read_text())
    post=data.get("post") or {}
    return {"available":True,"run_id":data.get("run_id"),
            "tests":sum(int(v.get("tests",0)) for v in post.values() if isinstance(v,dict)),
            "all_local_tests_passed":bool(post) and all(v.get("passed") is True for v in post.values() if isinstance(v,dict)),
            "independent_convergence":data.get("converged_tested_scope") is True,
            "outcome":data.get("stop_reason") or "completed",
            "production_changed":data.get("production_changed") is True}

def health():
    statuses={}
    for name in CONTAINERS:
        result=shell(["docker","inspect","--format","{{.State.Status}}",name],timeout=10)
        statuses[name]=result.stdout.strip() if result.returncode==0 else "missing"
    whatsapp={}
    for name in WHATSAPP:
        result=shell(["docker","inspect","--format","{{.State.Status}}",name],timeout=10)
        whatsapp[name]=result.stdout.strip() if result.returncode==0 else "missing"
    disk=shutil.disk_usage("/")
    mem={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemTotal:","MemAvailable:")):
            k,v=line.split(":",1);mem[k]=int(v.strip().split()[0])
    return {"containers":statuses,"all_containers_running":all(s=="running" for s in statuses.values()),
            "whatsapp_containers":whatsapp,"whatsapp_online":all(s=="running" for s in whatsapp.values()),
            "disk_free_percent":round(100*disk.free/disk.total,1),
            "memory_available_percent":round(100*mem.get("MemAvailable",0)/max(mem.get("MemTotal",1),1),1)}

INVENTORY_SQL=r"""
BEGIN TRANSACTION READ ONLY;
SELECT 'SM_INV_JSON=' || json_build_object(
'products_total',(SELECT count(*) FROM products),
'active_products',(SELECT count(*) FROM products WHERE activo=true),
'available_units',(SELECT coalesce(sum(cantidad_disponible),0) FROM stock),
'reserved_units',(SELECT coalesce(sum(cantidad_reservada),0) FROM stock),
'out_of_stock_active_products',(SELECT count(*) FROM products p WHERE p.activo=true
   AND NOT EXISTS(SELECT 1 FROM stock s WHERE s.product_id=p.id AND s.cantidad_disponible>0)),
'orders_total',(SELECT count(*) FROM orders),
'orders_pending',(SELECT count(*) FROM orders WHERE estado='pendiente'),
'orders_with_completed_at',(SELECT count(*) FROM orders WHERE completed_at IS NOT NULL)
)::text;
COMMIT;
"""

def inventory():
    result=shell(["runuser","-u","postgres","--","psql","-X","-At",
                  "-v","ON_ERROR_STOP=1","-d","inventory_db"],
                 input=INVENTORY_SQL,timeout=20)
    if result.returncode:raise RuntimeError("Inventory read-only aggregation unavailable")
    value=next((x[len("SM_INV_JSON="):] for x in result.stdout.splitlines()
                if x.startswith("SM_INV_JSON=")),None)
    if value is None:raise RuntimeError("Inventory aggregates missing")
    data=json.loads(value)
    required=("products_total","active_products","available_units","reserved_units",
              "out_of_stock_active_products","orders_total","orders_pending",
              "orders_with_completed_at")
    if not all(type(data.get(k)) is int and data[k]>=0 for k in required):
        raise RuntimeError("Inventory data invalid")
    return {"status":"ok","source":"inventory_db","read_only":True,**data}

def photos():
    path="file:/opt/softmobile-waha-test/staff-bridge/requests.sqlite3?mode=ro"
    pending=[]
    statuses={}
    with sqlite3.connect(path,uri=True,timeout=3) as db:
        db.execute("PRAGMA query_only=ON")
        for row_id,status,created in db.execute("SELECT id,status,created_at FROM requests"):
            statuses[str(status)]=statuses.get(str(status),0)+1
            if status in ("pending","assigned","answer_pending_review","ready_for_review"):
                try:
                    ago=(datetime.now(timezone.utc)-
                         datetime.fromisoformat(created.replace("Z","+00:00"))).total_seconds()
                except (ValueError,TypeError,AttributeError):
                    ago=0
                if ago>7200:pending.append(int(row_id))
    return {"status":"ok","source":"staff-bridge SQLite (read-only)",
            "status_counts":statuses,"older_than_2h_pending_review_ids":sorted(pending)}

def proposals(data):
    descriptions={"unanswered":"Responder consulta sin respuesta",
        "recoverable":"Revisar oportunidad de venta",
        "consented_followup":"Evaluar seguimiento con consentimiento; no enviar automáticamente",
        "human_review":"Escalar a persona antes de contactar"}
    return [{"conversation_id":id_,"type":type_,"action":descriptions[type_],"requires_approval":True}
            for type_,ids in data["queues"].items() for id_ in ids]

def save(path,content):
    fd,tmp=tempfile.mkstemp(prefix=".softmobile-",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        os.chown(tmp,0,1000);os.chmod(tmp,0o640);os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def markdown(r):
    c=r["chatwoot"];q=r["quality"];h=r["health"]
    counts={k:len(v) for k,v in c.get("queues",{}).items()}
    return "\n".join([
        "# OpenClaw | Supervisor SoftMobile",
        "Modo SOLO LECTURA: no enviar mensajes, cambiar precios, comprar, ni desplegar.",
        "Reporte UTC: "+r["captured_utc"],
        "Chatwoot: "+c.get("status","unavailable"),
        "Cobertura del buzón 2, cuenta 2: "+str(c.get("reviewed_conversations","?"))+"/"+str(c.get("total_conversations","?")),
        "Actividad 24h: "+str(c.get("recent_24h","?"))+"; abiertas: "+str(c.get("open_conversations","?")),
        "Colas (IDs solamente): "+json.dumps(counts,ensure_ascii=False),
        "Propuestas sujetas a aprobación: "+str(len(r["proposed_actions"])),
        "Inventario: "+str(r.get("inventory",{}).get("available_units","?"))+
        " unidades disponibles; "+str(r.get("inventory",{}).get("out_of_stock_active_products","?"))+
        " productos activos sin stock; "+str(r.get("inventory",{}).get("orders_pending","?"))+
        " registros de orden pendientes (no equivalen a entregas pendientes).",
        "Fotografías: solicitudes por estado "+json.dumps(r.get("photos",{}).get("status_counts",{}),ensure_ascii=False)+
        "; revisión de más de 2h "+str(r.get("photos",{}).get("older_than_2h_pending_review_ids",[])),
        "Pruebas locales: "+str(q.get("tests","?"))+"; correctas: "+str(q.get("all_local_tests_passed","?"))+
        "; revisión independiente convergente: "+str(q.get("independent_convergence","?")),
        "VPS: contenedores activos="+str(h.get("all_containers_running","?"))+
        "; WhatsApp WAHA activo="+str(h.get("whatsapp_online","?"))+
        "; disco libre="+str(h.get("disk_free_percent","?"))+
        "%; RAM disponible="+str(h.get("memory_available_percent","?"))+"%",
        "Alertas: "+("; ".join(r["alerts"]) if r["alerts"] else "ninguna"),
        "Consultar latest.json para IDs, nunca interpretar propuestas como ventas confirmadas.",
        ""
    ])

def collect():
    r={"schema_version":1,"captured_utc":datetime.now(timezone.utc).isoformat(),
       "mode":"read_only","public_messages_sent":0,"production_changed":False,
       "alerts":[],"proposed_actions":[]}
    try:
        r["chatwoot"]=chatwoot()
        r["proposed_actions"]=proposals(r["chatwoot"])
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as err:
        r["chatwoot"]={"status":"unavailable","coverage_complete":False}
        r["alerts"].append("Chatwoot: "+str(err)[:100])
    try:
        r["inventory"]=inventory()
        if r["inventory"]["orders_total"]>0 and r["inventory"]["orders_total"]==r["inventory"]["orders_pending"]:
            r["alerts"].append("Todas las órdenes están marcadas pendientes: comprobar si son pruebas o datos sin cerrar")
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as err:
        r["inventory"]={"status":"unavailable"};r["alerts"].append("Inventario: "+str(err)[:100])
    try:
        r["photos"]=photos()
        if r["photos"]["older_than_2h_pending_review_ids"]:
            r["alerts"].append("Solicitudes de fotos antiguas sin revisar; verificar si son pruebas")
    except (OSError,ValueError,sqlite3.Error) as err:
        r["photos"]={"status":"unavailable"};r["alerts"].append("Fotografías: "+str(err)[:100])
    try:
        r["quality"]=lab()
        if not r["quality"].get("all_local_tests_passed"):
            r["alerts"].append("Laboratorio no aprobado")
    except (OSError,ValueError):
        r["quality"]={"available":False};r["alerts"].append("Laboratorio inaccesible")
    try:
        r["health"]=health()
        if not r["health"]["all_containers_running"]:r["alerts"].append("Contenedor principal caído")
        if not r["health"]["whatsapp_online"]:r["alerts"].append("WhatsApp WAHA o su Redis detenido; no se reinicia automáticamente")
        if r["health"]["disk_free_percent"]<15:r["alerts"].append("Disco libre bajo")
        if r["health"]["memory_available_percent"]<10:r["alerts"].append("RAM libre baja")
    except (OSError,ValueError,subprocess.TimeoutExpired):
        r["health"]={"available":False};r["alerts"].append("Monitoreo VPS falló")
    return r

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result=collect()
    save(OUT/"latest.json",json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    save(OUT/"STATUS.md",markdown(result))
    print(json.dumps({"chatwoot":result["chatwoot"].get("status"),
          "reviewed":result["chatwoot"].get("reviewed_conversations"),
          "proposals":len(result["proposed_actions"]),
          "lab_passed":result["quality"].get("all_local_tests_passed"),
          "vps_running":result["health"].get("all_containers_running"),
          "alerts":result["alerts"]},ensure_ascii=False))
    return 0 if result["chatwoot"].get("status")=="ok" else 2

if __name__=="__main__":
    raise SystemExit(main())
