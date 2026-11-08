#!/usr/bin/env python3
"""Fail-closed Meta Ads analytics adapter: no campaign changes or assumptions.

Metricool observations come from an explicitly verified connector snapshot,
not from the VPS itself. A static, unrefreshed snapshot cannot authorize any
budget changes or ROI attribution.
"""
from __future__ import annotations
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
import json
from pathlib import Path

from supervisor import OUT,save

INPUT=OUT/"METRICOOL_SOURCE.json"
def as_nonnegative(value):
    try:v=Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError):raise ValueError("invalid metric")
    if not v.is_finite() or v<0:raise ValueError("invalid metric")
    return v

def validate(item,now=None):
    if (not isinstance(item,dict) or
        item.get("source")!="metricool_meta_ads_read_only" or
        item.get("business_alias")!="softmobile" or
        item.get("network")!="metaAds" or
        item.get("campaigns_returned") is None or
        type(item.get("campaigns_returned")) is not int or
        type(item.get("daily_rows_returned")) is not int or
        type(item.get("refresh_automated")) is not bool or
        item.get("any_campaign_modified") is not False or
        item.get("read_only") is not True):
        raise ValueError("invalid ads source")
    if not 0<=item["campaigns_returned"]<=10000 or not 0<=item["daily_rows_returned"]<=90:
        raise ValueError("invalid ads counts")
    if set(item.get("fields",[]))!={"FAEV01","FAEV04","FAEV05"}:
        raise ValueError("wrong metric fields")
    for key in ("impressions_reported","spend_reported","clicks_reported"):
        as_nonnegative(item.get(key))
    cap=datetime.now(timezone.utc) if now is None else now
    at=datetime.fromisoformat(item["captured_utc"].replace("Z","+00:00"))
    age=(cap-at).total_seconds()
    if not 0<=age<86400:
        raise ValueError("ads source stale")
    if item.get("client_sales_attributed_verified") is not False:
        raise ValueError("unverified sales attribution")
    return item

def analyze(item,now=None):
    source=validate(item,now)
    # Presence of a connected analytics provider does not demonstrate active
    # campaigns, spend currency, attribution or conversions.
    evidence_has_campaigns=(source["campaigns_returned"]>0 and
                            source["daily_rows_returned"]>0 and
                            as_nonnegative(source["impressions_reported"])>0)
    report={
        "schema_version":1,"mode":"ads_read_only_evidence",
        "at":(now or datetime.now(timezone.utc)).isoformat(),
        "source_utc":source["captured_utc"],
        "source":"Metricool connector, imported read-only",
        "daily_rows_returned":source["daily_rows_returned"],
        "campaigns_returned":source["campaigns_returned"],
        "impressions_reported":str(as_nonnegative(source["impressions_reported"])),
        "spend_reported":str(as_nonnegative(source["spend_reported"])),
        "clicks_reported":str(as_nonnegative(source["clicks_reported"])),
        "currency_verified":False,
        "performance_data_present":bool(evidence_has_campaigns),
        "campaign_delivery_independently_verified":False,
        "client_sales_attributed_verified":False,
        "ads_data_integrated_into_vps":False,
        "automated_refresh":source["refresh_automated"],
        "ads_optimization_permitted":False,
        "campaigns_modified":0,
        "public_messages_sent":0,
        "production_changed":False}
    return report

def markdown(out):
    return "\n".join([
        "# SoftMobile — Publicidad: fuente conectada, optimización bloqueada",
        "Captura UTC: "+out["source_utc"],
        "Filas diarias del conector: "+str(out["daily_rows_returned"]),
        "Campañas con datos: "+str(out["campaigns_returned"]),
        "Impresiones indicadas: "+out["impressions_reported"],
        "Clics indicados: "+out["clicks_reported"],
        "Gasto indicado: "+out["spend_reported"]+" (moneda NO verificada).",
        "No es prueba de que no existan campañas o gasto en otra fuente.",
        "Sin retorno automático hacia VPS ni conversiones verificadas.",
        "Acciones sobre anuncios, presupuesto y segmentación: BLOQUEADAS.",
        "Exige conexión verificable a las campañas y fuentes de cierres reales.",
        ""
    ])

def main():
    try:
        data=json.loads(INPUT.read_text())
        report=analyze(data)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        print("ads_source_not_verifiable")
        return 2
    save(OUT/"MARKETING_AUDIT.json",json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    save(OUT/"MARKETING_AUDIT.md",markdown(report))
    print(json.dumps({"metricool_rows":report["daily_rows_returned"],
                      "campaign_rows":report["campaigns_returned"],
                      "ads_optimization_permitted":False,"client_sales_attributed":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
