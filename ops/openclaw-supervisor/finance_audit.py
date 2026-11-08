#!/usr/bin/env python3
"""Privacy-preserving, READ ONLY finance and inventory reconciliation signals.

This is not a P&L. Pending orders are pipeline, NOT revenue. The tool has no
write pathway to PostgreSQL, any payment gateway, buyers or vendor services.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import subprocess

from supervisor import OUT, save

QUERY=r"""
BEGIN TRANSACTION READ ONLY;
SELECT 'SM_FINANCE_AUDIT='||json_build_object(
 'orders', (SELECT count(*) FROM orders),
 'orders_by_state',(SELECT coalesce(json_object_agg(estado,n),'{}'::json)
    FROM (SELECT coalesce(estado,'unknown') estado,count(*) n FROM orders GROUP BY 1) s),
 'orders_validated', (SELECT count(*) FROM orders WHERE validada_at IS NOT NULL),
 'orders_completed', (SELECT count(*) FROM orders WHERE completed_at IS NOT NULL),
 'orders_validated_without_completion',(SELECT count(*) FROM orders
   WHERE validada_at IS NOT NULL AND completed_at IS NULL),
 'orders_completed_without_validation',(SELECT count(*) FROM orders
   WHERE completed_at IS NOT NULL AND validada_at IS NULL),
 'orders_without_items',(SELECT count(*) FROM orders o WHERE NOT EXISTS
    (SELECT 1 FROM order_items oi WHERE oi.order_id=o.id)),
 'orphan_order_items',(SELECT count(*) FROM order_items oi WHERE NOT EXISTS
    (SELECT 1 FROM orders o WHERE o.id=oi.order_id)),
 'bad_order_quantities',(SELECT count(*) FROM order_items WHERE cantidad<=0),
 'order_item_missing_cost',(SELECT count(*) FROM order_items WHERE costo_unitario IS NULL),
 'negative_item_prices',(SELECT count(*) FROM order_items
    WHERE precio_unitario<0 OR costo_unitario<0),
 'order_total_item_mismatch',(SELECT count(*) FROM orders o
    WHERE EXISTS(SELECT 1 FROM order_items oi WHERE oi.order_id=o.id)
    AND ABS(coalesce(o.total,0)-coalesce(
         (SELECT sum(oi.precio_unitario*oi.cantidad) FROM order_items oi
          WHERE oi.order_id=o.id),0))>0.01),
 'mismatch_by_payment',(SELECT coalesce(json_object_agg(method,mismatch),'{}'::json)
    FROM (SELECT coalesce(o.metodo_pago,'unknown') method,
      count(*) FILTER (WHERE ABS(coalesce(o.total,0)-coalesce(items.subtotal,0))>0.01) mismatch
      FROM orders o JOIN LATERAL
        (SELECT sum(oi.precio_unitario*oi.cantidad) subtotal FROM order_items oi
         WHERE oi.order_id=o.id) items ON TRUE
      GROUP BY 1) x),
 'pending_orders_older_than_30d',(SELECT count(*) FROM orders
    WHERE estado='pendiente' AND created_at<now()-interval '30 days'),
 'duplicate_transfer_references',(SELECT coalesce(sum(n-1),0) FROM
     (SELECT count(*) n FROM orders
      WHERE transfer_reference_normalized IS NOT NULL AND
            LENGTH(TRIM(transfer_reference_normalized))>=5
      GROUP BY transfer_reference_normalized HAVING count(*)>1) refs),
 'daily_closes',(SELECT count(*) FROM location_daily_closes),
 'approved_closes',(SELECT count(*) FROM location_daily_closes WHERE approved_at IS NOT NULL),
 'close_discrepancies',(SELECT count(*) FROM location_daily_closes
   WHERE ABS(coalesce(difference,0))>0.01),
 'stock_negative_rows',(SELECT count(*) FROM stock
    WHERE cantidad_disponible<0 OR cantidad_reservada<0 OR cantidad_defectuosa<0),
 'stock_reserved_more_than_available',(SELECT count(*) FROM stock
    WHERE cantidad_reservada>cantidad_disponible AND cantidad_disponible>=0),
 'products_missing_cost',(SELECT count(*) FROM products
    WHERE activo IS TRUE AND costo IS NULL),
 'products_price_below_cost',(SELECT count(*) FROM products
    WHERE activo IS TRUE AND precio IS NOT NULL AND costo IS NOT NULL
    AND precio<costo),
 'products_active_out_of_stock',(SELECT count(*) FROM products p WHERE activo IS TRUE
    AND NOT EXISTS(SELECT 1 FROM stock s WHERE s.product_id=p.id
    AND s.cantidad_disponible>0)),
 'transfers_confirmed_zero_received',(SELECT count(*) FROM stock_transfers
    WHERE estado='confirmada' AND coalesce(received_quantity,0)=0),
 'transfers_confirmed_missing_quantity',(SELECT count(*) FROM stock_transfers
    WHERE estado='confirmada' AND coalesce(missing_quantity,0)>0),
 'transfer_overreceived',(SELECT count(*) FROM stock_transfers
    WHERE received_quantity IS NOT NULL AND
         received_quantity>cantidad),
 'recent_completed_orders_7d',(SELECT count(*) FROM orders
    WHERE completed_at>=now()-interval '7 days')
)::text;
COMMIT;
"""
COUNTS=("orders","orders_validated","orders_completed","orders_validated_without_completion",
    "orders_completed_without_validation","orders_without_items","orphan_order_items",
    "bad_order_quantities","order_item_missing_cost","negative_item_prices",
    "order_total_item_mismatch","pending_orders_older_than_30d",
    "duplicate_transfer_references","daily_closes","approved_closes","close_discrepancies",
    "stock_negative_rows","stock_reserved_more_than_available","products_missing_cost",
    "products_price_below_cost","products_active_out_of_stock",
    "transfers_confirmed_zero_received","transfers_confirmed_missing_quantity",
    "transfer_overreceived","recent_completed_orders_7d")
ISSUES={
  "orphan_order_items":"CRITICAL","orders_completed_without_validation":"CRITICAL",
  "stock_negative_rows":"CRITICAL","transfer_overreceived":"CRITICAL",
  "order_total_item_mismatch":"REVIEW","duplicate_transfer_references":"REVIEW",
  "orders_without_items":"REVIEW","bad_order_quantities":"REVIEW",
  "negative_item_prices":"REVIEW","close_discrepancies":"REVIEW",
  "transfers_confirmed_zero_received":"REVIEW",
  "transfers_confirmed_missing_quantity":"REVIEW",
  "stock_reserved_more_than_available":"REVIEW",
  "products_missing_cost":"REVIEW","products_price_below_cost":"REVIEW",
  "order_item_missing_cost":"REVIEW",
  "orders_validated_without_completion":"REVIEW"}
def validate(data):
    if not isinstance(data,dict) or not isinstance(data.get("orders_by_state"),dict):
        raise ValueError("finance source invalid")
    for name in COUNTS:
        if type(data.get(name)) is not int or data[name]<0:
            raise ValueError("finance count invalid: "+name)
    counts=data["orders_by_state"]
    mismatches=data.get("mismatch_by_payment")
    if (not isinstance(mismatches,dict) or
        any(not isinstance(k,str) or type(v) is not int or v<0
            for k,v in mismatches.items()) or
        sum(mismatches.values())!=data["order_total_item_mismatch"]):
        raise ValueError("payment method mismatch counts inconsistent")
    if (any(not isinstance(k,str) or type(v) is not int or v<0 for k,v in counts.items())
        or sum(counts.values())!=data["orders"]
        or data["orders_completed"]>data["orders"]
        or data["orders_validated"]>data["orders"]
        or data["approved_closes"]>data["daily_closes"]
        or data["recent_completed_orders_7d"]>data["orders_completed"]):
        raise ValueError("finance count consistency failed")
    return data

def query():
    p=subprocess.run(["runuser","-u","postgres","--","psql","-X","-At",
                     "-v","ON_ERROR_STOP=1","-d","inventory_db"],
        input=QUERY,text=True,capture_output=True,timeout=20,check=False)
    if p.returncode:
        raise RuntimeError("finance SQL read-only query failed")
    matched=[row[len("SM_FINANCE_AUDIT="):] for row in p.stdout.splitlines()
             if row.startswith("SM_FINANCE_AUDIT=")]
    if len(matched)!=1:raise RuntimeError("finance SQL response invalid")
    return validate(json.loads(matched[0]))

def analyze(data,at=None,source_utc=None):
    data=validate(data)
    counts={k:data[k] for k in COUNTS}
    issue_list=[{"code":k,"severity":severity,"count":data[k]}
                for k,severity in ISSUES.items() if data[k]>0]
    financial_ready=(data["orders_completed"]>0 and
        data["approved_closes"]>0 and
        data["orders_completed_without_validation"]==0 and
        data["order_item_missing_cost"]==0 and
        data["order_total_item_mismatch"]==0)
    # Still not a verified profit: cash receipts, returns, taxes and fees
    # must be reconciled against bank/payment records by a trusted source.
    result={
      "schema_version":1,"mode":"finance_read_only_audit",
      "at":at or datetime.now(timezone.utc).isoformat(),
      "source_utc":source_utc,
      "source":"inventory_db","read_only":True,"customer_data_extracted":False,
      "raw_customer_records":0,"counts":counts,
      "orders_by_state":data["orders_by_state"],
      "mismatch_by_payment":data["mismatch_by_payment"],
      "card_and_financing_mismatches_may_include_fees":True,
      "flags":issue_list,"flag_count":len(issue_list),
      "has_completed_orders":data["orders_completed"]>0,
      "has_approved_daily_close":data["approved_closes"]>0,
      "financial_reconciliation_prerequisites":financial_ready,
      "profit_verified":False,"revenue_verified":False,
      "pending_orders_not_revenue":True,"public_messages_sent":0,
      "inventory_modified":False,"payments_initiated":0,
      "requires_human_accounting_review":True
    }
    return result

def markdown(d):
    lines=["# SoftMobile — auditoría financiera interna sin datos personales",
        "Ejecución UTC: "+d["at"],
        "Fuente: inventario_db, transacción SELECT ONLY.",
        "No se comprueba beneficio, caja real ni ingresos mediante órdenes pendientes.",
        "Ventas completadas: "+str(d["counts"]["orders_completed"])+
         " | Cierres aprobados: "+str(d["counts"]["approved_closes"])+
         " | Órdenes pendientes: "+str(d["orders_by_state"].get("pendiente",0)),
        "Ingresos verificados: NO. Utilidad verificada: NO.",
        "Los totales de tarjeta y financiamiento pueden incluir recargos/comisiones.",
        "Diferencias por método (no equivalen a errores contables): "+
         json.dumps(d["mismatch_by_payment"],ensure_ascii=False,sort_keys=True),
        "","## Anomalías agregadas; requieren conciliación"]
    lines+=["- "+x["severity"]+" / "+x["code"]+": "+str(x["count"])
            for x in d["flags"]] or ["- Sin anomalías en los conteos analizados; no prueba conciliación."]
    lines.extend(["","## Límites","Solo agregados, sin nombre, teléfono ni referencia bancaria.",
       "Revisar recibos, devoluciones, costos, tasas de tarjeta y cierres diarios antes de calcular utilidades.",
       "No realizar cobros, movimientos de stock, cierres ni compras por este informe."])
    return "\n".join(lines)+"\n"

def main():
    try:
        source=json.loads((OUT/"OPERATOR.json").read_text())
        director=json.loads((OUT/"DIRECTOR.json").read_text())
        timestamp=source.get("source_utc")
        if (source.get("mode")!="internal_actions_only" or
            source.get("failures")!=0 or
            source.get("public_messages_sent")!=0 or
            source.get("external_actions")!=0 or
            director.get("source_utc")!=timestamp):
            raise ValueError("unsafe finance operator source")
        age=(datetime.now(timezone.utc)-
             datetime.fromisoformat(timestamp.replace("Z","+00:00"))).total_seconds()
        if not 0<=age<=5400:
            raise ValueError("stale finance source")
        d=analyze(query(),source_utc=timestamp)
    except (OSError,ValueError,RuntimeError,TypeError,subprocess.TimeoutExpired,AttributeError):
        print('finance_audit_blocked')
        return 2
    save(OUT/"FINANCE_AUDIT.json",json.dumps(d,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"FINANCE_AUDIT.md",markdown(d))
    print(json.dumps({"status":"ok","flags":d["flag_count"],"completed":
        d["counts"]["orders_completed"],"approved_closes":
        d["counts"]["approved_closes"],"revenue_verified":False},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
