"""Business-insights route aligned with canonical financial accounting."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session, joinedload

from app.auth import check_permission
from app.config_production import prod_settings
from app.database import get_db
from app.models import Location, Order, OrderItem, Product, SalesProfile, Stock, User
from app.routers.ai_intelligence import (
    BusinessInsightRecommendation,
    BusinessInsightSlowMover,
    BusinessInsightStockAlert,
    BusinessInsightTopSeller,
    BusinessInsightTrendPoint,
    BusinessInsightsFilters,
    BusinessInsightsKPIs,
    BusinessInsightsMetrics,
    BusinessInsightsRequest,
    BusinessInsightsResponse,
    FINAL_SALE_STATUSES,
    _build_fallback_recommendations,
    _business_insights_cache_ttl,
    _cleanup_business_insights_cache,
    _ensure_aware,
    _get_business_insights_cache,
    _isoformat,
    _make_business_insights_cache_key,
    _parse_ai_business_response,
    _safe_float,
    _utcnow,
    openai_service,
)
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.order_integrity import effective_sale_at, effective_sale_column


router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/business-insights", response_model=BusinessInsightsResponse)
def generate_business_insights_integrity(
    payload: BusinessInsightsRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view")),
):
    """Generate business insights from finalized-sale time and historical COGS."""
    days = max(7, min(payload.days, 120))
    now = _utcnow()
    period_start = now - timedelta(days=days)

    sales_profile_id = payload.sales_profile_id
    if payload.sales_profile_slug:
        profile = db.query(SalesProfile).filter(SalesProfile.slug == payload.sales_profile_slug).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Sales Profile not found")
        sales_profile_id = profile.id
    elif sales_profile_id:
        profile = db.query(SalesProfile).filter(SalesProfile.id == sales_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Sales Profile not found")

    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    scoped_location_ids = accessible_location_ids
    if payload.location_id:
        location_exists = db.query(Location).filter(Location.id == payload.location_id).first()
        if not location_exists:
            raise HTTPException(status_code=404, detail="Location not found")
        require_location_access(db, current_user, payload.location_id, "can_view")
        scoped_location_ids = [payload.location_id]
    if scoped_location_ids is not None:
        scoped_location_ids = sorted(scoped_location_ids)

    cache_store = _get_business_insights_cache(request)
    cache_key = _make_business_insights_cache_key(days, payload, scoped_location_ids)
    cache_entry = cache_store.get(cache_key) if payload.use_cache and not payload.force_refresh else None
    if cache_entry and cache_entry.get("expires_at") and cache_entry["expires_at"] > now:
        response.headers["X-AI-Business-Cache"] = "HIT"
        cached_value = cache_entry.get("value")
        if isinstance(cached_value, BusinessInsightsResponse):
            return cached_value.model_copy(deep=True)
        return cached_value

    sale_at_column = effective_sale_column(Order)
    orders_query = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(sale_at_column >= period_start)
        .filter(Order.estado.in_(FINAL_SALE_STATUSES))
    )
    if sales_profile_id:
        orders_query = orders_query.filter(Order.sales_profile_id == sales_profile_id)
    if payload.location_id:
        orders_query = orders_query.filter(Order.source_location_id == payload.location_id)
    elif scoped_location_ids is not None:
        orders_query = orders_query.filter(Order.source_location_id.in_(scoped_location_ids))

    orders = orders_query.all()

    sales_map: Dict[int, Dict[str, Any]] = {}
    daily_revenue = defaultdict(float)
    total_revenue = 0.0
    gross_profit_total = 0.0

    for order in orders:
        order_total = _safe_float(order.total)
        total_revenue += order_total
        sale_at = _ensure_aware(effective_sale_at(order))
        if sale_at:
            daily_revenue[sale_at.date().isoformat()] += order_total

        for item in order.items:
            product = item.product
            if not product:
                continue
            entry = sales_map.setdefault(
                product.id,
                {
                    "product_name": product.nombre,
                    "units_sold": 0,
                    "revenue": 0.0,
                    "gross_profit": 0.0,
                    "last_sale_at": None,
                },
            )
            entry["units_sold"] += item.cantidad
            item_revenue = _safe_float(item.precio_unitario) * item.cantidad
            entry["revenue"] += item_revenue
            historical_cost = item.costo_unitario if item.costo_unitario is not None else product.costo
            item_cost = _safe_float(historical_cost) * item.cantidad
            profit = item_revenue - item_cost
            entry["gross_profit"] += profit
            gross_profit_total += profit
            if sale_at:
                last_sale_at = entry.get("last_sale_at")
                if not last_sale_at or sale_at > last_sale_at:
                    entry["last_sale_at"] = sale_at

    orders_count = len(orders)
    avg_order_value = total_revenue / orders_count if orders_count else 0.0

    products_query = (
        db.query(Product)
        .options(joinedload(Product.stock_items).joinedload(Stock.location))
        .filter(Product.activo == True)
    )
    if scoped_location_ids is not None:
        products_query = products_query.join(Stock, Stock.product_id == Product.id).filter(
            Stock.location_id.in_(scoped_location_ids)
        ).distinct()
    products = products_query.all()

    top_sellers = [
        {
            "product_id": product_id,
            "product_name": data["product_name"],
            "units_sold": data["units_sold"],
            "revenue": round(data["revenue"], 2),
            "gross_profit": round(data["gross_profit"], 2),
        }
        for product_id, data in sales_map.items()
        if data["units_sold"] > 0
    ]
    top_sellers.sort(key=lambda item: item["revenue"], reverse=True)
    top_sellers = top_sellers[:5]

    slow_movers: List[Dict[str, Any]] = []
    stock_alerts: List[Dict[str, Any]] = []

    for product in products:
        stock_available = 0
        for stock in product.stock_items:
            if scoped_location_ids is not None and stock.location_id not in scoped_location_ids:
                continue
            stock_available += max(0, (stock.cantidad_disponible or 0) - (stock.cantidad_reservada or 0))

        if stock_available <= 0:
            continue

        sale_info = sales_map.get(product.id)
        last_sale_at: Optional[datetime] = sale_info.get("last_sale_at") if sale_info else None
        days_without_sales = (now - last_sale_at).days if last_sale_at else days + 30
        units_sold = sale_info["units_sold"] if sale_info else 0

        if units_sold == 0 or days_without_sales > max(14, days // 2):
            slow_movers.append(
                {
                    "product_id": product.id,
                    "product_name": product.nombre,
                    "stock_available": stock_available,
                    "days_without_sales": int(days_without_sales),
                    "last_sale_at": _isoformat(last_sale_at),
                }
            )

        avg_daily_demand = (sale_info["units_sold"] / days) if sale_info and days else 0.0
        days_until_stockout = (stock_available / avg_daily_demand) if avg_daily_demand > 0 else None
        if avg_daily_demand > 0 and stock_available < max(5, avg_daily_demand * 5):
            stock_alerts.append(
                {
                    "product_id": product.id,
                    "product_name": product.nombre,
                    "stock_available": stock_available,
                    "avg_daily_demand": round(avg_daily_demand, 2),
                    "days_until_stockout": round(days_until_stockout, 1) if days_until_stockout else None,
                }
            )

    slow_movers.sort(key=lambda item: (item["days_without_sales"], item["stock_available"]), reverse=True)
    slow_movers = slow_movers[:5]
    stock_alerts.sort(key=lambda item: item["days_until_stockout"] if item["days_until_stockout"] is not None else 9999)
    stock_alerts = stock_alerts[:5]

    revenue_trends = [
        {"date": date_key, "revenue": round(value, 2)}
        for date_key, value in sorted(daily_revenue.items())
    ][-14:]

    metrics_model = BusinessInsightsMetrics(
        kpis=BusinessInsightsKPIs(
            total_revenue=round(total_revenue, 2),
            orders_count=orders_count,
            avg_order_value=round(avg_order_value, 2),
            gross_margin_estimate=round(gross_profit_total, 2),
        ),
        top_sellers=[BusinessInsightTopSeller(**item) for item in top_sellers],
        slow_movers=[BusinessInsightSlowMover(**item) for item in slow_movers],
        stock_alerts=[BusinessInsightStockAlert(**item) for item in stock_alerts],
        revenue_trends=[BusinessInsightTrendPoint(**item) for item in revenue_trends],
    )

    recommendations: List[BusinessInsightRecommendation] = []
    ai_summary: Optional[str] = None
    tokens_used = 0
    raw_response: Optional[str] = None
    metrics_payload = metrics_model.model_dump()

    if prod_settings.ENABLE_AI_FEATURES and prod_settings.OPENAI_API_KEY:
        try:
            metrics_json = json.dumps(metrics_payload, ensure_ascii=False)
            prompt = (
                "Analiza el siguiente JSON de métricas y devuelve recomendaciones accionables. "
                "Responde ÚNICAMENTE JSON con summary y recommendations; cada recomendación "
                "debe contener title, action, impact, category y priority.\n"
                f"Contexto:\n{metrics_json}"
            )
            completion = openai_service.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un analista de retail que entrega planes concretos basados en datos."},
                    {"role": "user", "content": prompt},
                ],
                model=prod_settings.OPENAI_MODEL,
                temperature=0.4,
            )
            raw_response = completion.get("reply") or ""
            tokens_used = int((completion.get("usage") or {}).get("total_tokens") or 0)
            parsed = _parse_ai_business_response(raw_response)
            ai_summary = parsed.get("summary")
            for rec in parsed.get("recommendations", []) or []:
                action = rec.get("action") or rec.get("recommendation")
                title = rec.get("title") or rec.get("headline") or action or "Recomendación"
                priority = (rec.get("priority") or "media").lower()
                if priority not in {"alta", "media", "baja", "critica"}:
                    priority = "media"
                recommendations.append(
                    BusinessInsightRecommendation(
                        title=title,
                        action=action or title,
                        impact=rec.get("impact"),
                        category=rec.get("category"),
                        priority=priority,
                    )
                )
        except RuntimeError:
            # Heuristics remain available when the provider fails.
            pass

    if not recommendations:
        recommendations = _build_fallback_recommendations(metrics_payload)
        if not ai_summary:
            ai_summary = "Se generaron recomendaciones basadas en heurísticas locales."

    result = BusinessInsightsResponse(
        generated_at=_utcnow(),
        period_days=days,
        filters=BusinessInsightsFilters(
            location_id=payload.location_id,
            sales_profile_id=sales_profile_id,
            sales_profile_slug=payload.sales_profile_slug,
        ),
        metrics=metrics_model,
        recommendations=recommendations,
        ai_summary=ai_summary,
        tokens_used=tokens_used,
        raw_response=raw_response,
    )

    if payload.use_cache:
        _cleanup_business_insights_cache(cache_store)
        cache_store[cache_key] = {
            "expires_at": _utcnow() + timedelta(seconds=_business_insights_cache_ttl()),
            "value": result.model_copy(deep=True),
        }
        response.headers.setdefault("X-AI-Business-Cache", "MISS")
    else:
        response.headers.setdefault("X-AI-Business-Cache", "BYPASS")
    return result
