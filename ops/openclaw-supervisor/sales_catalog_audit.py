#!/usr/bin/env python3
"""Sales-only PostgreSQL aggregate catalog gate, never price quotations.

Reads only counts, inside one explicit READ ONLY transaction. Produces
redacted observations for the autonomous seller laboratory; no product/SKU,
customer identifiers, prices, locations or personal data in the output.

A database record is NOT fresh/authoritative partner inventory. This check
cannot authorize a public quote, purchase, discount or deployment.
"""
import json
import re
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from supervisor import OUT,save

MARK="SM_CATALOG_QA="
PATH=OUT/"CATALOG_AUDIT.json"
SQL=r"""
BEGIN TRANSACTION READ ONLY;
SELECT 'SM_CATALOG_QA=' || json_build_object(
 'active_products',(SELECT count(*) FROM products p WHERE p.activo=true),
 'stocked_active_products',(SELECT count(DISTINCT p.id) FROM products p
    JOIN stock s ON s.product_id=p.id JOIN locations l ON s.location_id=l.id
    WHERE p.activo=true AND l.activo=true AND s.cantidad_disponible>0),
 'stocked_fully_specified',(SELECT count(DISTINCT p.id) FROM products p
    JOIN stock s ON s.product_id=p.id JOIN locations l ON s.location_id=l.id
    WHERE p.activo=true AND l.activo=true AND s.cantidad_disponible>0
    AND p.precio>0 AND p.moneda='HNL'
    AND length(trim(coalesce(p.modelo,'')))>0
    AND length(trim(coalesce(p.color,'')))>0
    AND length(trim(coalesce(p.capacidad,'')))>0),
 'active_no_model',(SELECT count(*) FROM products p
    WHERE p.activo=true AND coalesce(trim(p.modelo),'')=''),
 'active_no_color',(SELECT count(*) FROM products p
    WHERE p.activo=true AND coalesce(trim(p.color),'')=''),
 'active_no_capacity',(SELECT count(*) FROM products p
    WHERE p.activo=true AND coalesce(trim(p.capacidad),'')=''),
 'active_no_price',(SELECT count(*) FROM products p
    WHERE p.activo=true AND (p.precio IS NULL OR p.precio<=0)),
 'active_no_cost',(SELECT count(*) FROM products p
    WHERE p.activo=true AND (p.costo IS NULL OR p.costo<=0)),
 'active_price_below_cost',(SELECT count(*) FROM products p
    WHERE p.activo=true AND p.precio IS NOT NULL AND p.costo IS NOT NULL AND p.precio<p.costo),
 'active_non_hnl',(SELECT count(*) FROM products p
    WHERE p.activo=true AND coalesce(p.moneda,'')<>'HNL'),
 'stocked_in_inactive_locations',(SELECT count(DISTINCT p.id) FROM products p
    JOIN stock s ON s.product_id=p.id JOIN locations l ON s.location_id=l.id
    WHERE p.activo=true AND l.activo=false AND s.cantidad_disponible>0)
)::text;
ROLLBACK;
"""
COUNTS=(
 "active_products","stocked_active_products","stocked_fully_specified",
 "active_no_model","active_no_color","active_no_capacity",
 "active_no_price","active_no_cost","active_price_below_cost",
 "active_non_hnl","stocked_in_inactive_locations"
)
class Reject(ValueError):pass
def utc():return datetime.now(timezone.utc).isoformat()
def validate(raw):
 if not isinstance(raw,dict) or set(raw)!=set(COUNTS):
  raise Reject("missing or extra aggregate fields")
 if any(type(raw[k]) is not int or raw[k]<0 for k in COUNTS):
  raise Reject("invalid aggregate count")
 n=raw["active_products"]
 if n>200000 or raw["stocked_active_products"]>n or \
    raw["stocked_fully_specified"]>raw["stocked_active_products"] or \
    any(raw[k]>n for k in COUNTS if k not in
      ("stocked_active_products","stocked_fully_specified")):
  raise Reject("impossible aggregate")
 return dict(raw)
def query(runner=subprocess.run):
 cmd=["runuser","-u","postgres","--",
      "psql","-X","-At","-v","ON_ERROR_STOP=1","-d","inventory_db"]
 try:done=runner(cmd,input=SQL,text=True,capture_output=True,check=False,timeout=20)
 except (subprocess.TimeoutExpired,OSError) as e:raise Reject("read-only db unavailable") from e
 if done.returncode!=0:raise Reject("read-only db query failed")
 rows=[line.removeprefix(MARK) for line in done.stdout.splitlines()
       if line.startswith(MARK)]
 if len(rows)!=1:raise Reject("incomplete catalog aggregate")
 try:return validate(json.loads(rows[0]))
 except (json.JSONDecodeError,KeyError,TypeError) as e:raise Reject("invalid db aggregate") from e

def report(data,now=None):
 vals=validate(data)
 stamped=now or utc()
 return {
  "schema_version":1,"mode":"read_only_sales_catalog_aggregate",
  "scope":"sales_only","at":stamped,"source_utc":stamped,
  "counts":{**vals,
    "active_without_stock":vals["active_products"]-vals["stocked_active_products"],
    "stocked_missing_required_quote_fields":
       vals["stocked_active_products"]-vals["stocked_fully_specified"]},
  "source":"ERP_database_internal_only",
  "model_color_capacity_price_db_fields_present":True,
  "partner_stock_connected":False,
  "stock_freshness_verified":False,
  "price_freshness_verified":False,
  "outbound_customer_quote_authorized":False,
  "public_release_permitted":False,
  "marketing_roi_verified":False,
  "payments_initiated":0,"inventory_updated":False,
  "public_messages_sent":0,"customer_data_extracted":False,
  "raw_price_or_cost_extracted":False,
  "sku_or_serial_extracted":False
 }
def main():
 try:obj=report(query())
 except (ValueError,Reject):
  print("catalog_audit_source_unavailable_or_invalid");return 2
 save(PATH,json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
 counts=obj["counts"]
 save(OUT/"CATALOG_AUDIT.md",
   "# SoftMobile — calidad de catálogo para ventas (solo lectura)\n\n"+
   "Datos agregados ERP, no disponibilidad ni precios autorizados para público.\n"+
   f"Productos activos: {counts['active_products']}.\n"+
   f"Con stock positivo en ubicaciones activas: {counts['stocked_active_products']}.\n"+
   f"Con modelo, color, capacidad, moneda HNL y precio: {counts['stocked_fully_specified']}.\n"+
   f"Precio inferior al costo registrado: {counts['active_price_below_cost']} (revisar; no afirmar pérdida).\n"+
   "Sin confirmación externa de stock ni vigencia de precios. Sin cambios reales.\n")
 print(json.dumps({"status":"sales_catalog_aggregates_checked",
    "active":counts["active_products"],
    "stocked":counts["stocked_active_products"],
    "fully_specified":counts["stocked_fully_specified"],
    "price_below_cost":counts["active_price_below_cost"],
    "outbound_customer_quote_authorized":False,
    "public_messages_sent":0},ensure_ascii=False))
 return 0
if __name__=="__main__":
 raise SystemExit(main())
