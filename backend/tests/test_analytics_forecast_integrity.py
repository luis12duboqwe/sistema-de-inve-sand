"""Regressions for final sales, HNL valuation and forecast cache."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from app.models import Order
from app.routers import analytics
from app.schemas import ForecastAnalyticsRequest, SalesForecast
from .helpers import seed_location_and_sales_profile, seed_product

def test_final_sale_time_not_old_creation_time(client, db_session):
    location, seller = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id, categoria="accesorio", is_serialized=False,
                           sku="FORECAST-COMPLETION-TEST", precio=500, costo=150)
    posted = client.post("/api/orders", json={
        "sales_profile_slug": seller.slug, "source_location_id": location.id,
        "canal": "tienda", "customer_name": "Venta finalizada",
        "customer_phone": "70112288", "metodo_pago": "efectivo",
        "items": [{"product_id": product["id"], "cantidad": 1, "precio_unitario": 500}],
    })
    assert posted.status_code == 201, posted.text
    order_id = posted.json()["id"]
    assert client.put(f"/api/orders/{order_id}/status", json={"estado": "completada"}).status_code == 200
    order = db_session.get(Order, order_id)
    order.created_at = datetime.now() - timedelta(days=100)
    order.completed_at = datetime.now()
    db_session.commit()
    dashboard = client.get("/api/analytics/dashboard").json()
    assert dashboard["total_orders_today"] == 1
    assert Decimal(str(dashboard["total_revenue_today"])) == Decimal("500")
    forecasts = client.post("/api/analytics/forecast", json={"product_ids": [product["id"]], "days_history": 60})
    assert forecasts.status_code == 200, forecasts.text
    assert forecasts.json()["forecasts"][0]["average_daily_sales"] > 0

def test_dashboard_normalizes_usd_cost_to_hnl(client, db_session):
    location, _ = seed_location_and_sales_profile(db_session)
    seed_product(client, location.id, sku="VAL-HNL-001", is_serialized=False,
                 categoria="accesorio", stock_inicial=1, costo=100, precio=100, moneda="Lps")
    seed_product(client, location.id, sku="VAL-USD-001", is_serialized=False,
                 categoria="accesorio", stock_inicial=1, costo=100, precio=100, moneda="USD")
    result = client.get("/api/analytics/dashboard")
    assert result.status_code == 200, result.text
    assert Decimal(str(result.json()["total_inventory_value"])) == Decimal("2600")

def test_forecast_cache_history_limit_and_expiration(monkeypatch, db_session):
    calls = []
    monkeypatch.setattr(analytics, "get_accessible_location_ids", lambda *_args: None)
    def generate(_db, *, days_history, **_kwargs):
        calls.append(days_history)
        return [
            SalesForecast(product_id=i, product_name=f"SKU {i}", current_stock=10,
                          average_daily_sales=1.0, predicted_sales_next_7_days=7,
                          predicted_sales_next_30_days=30, days_until_stockout=i,
                          restock_recommendation=20, confidence=0.8, trend="stable")
            for i in range(1, 4)
        ]
    monkeypatch.setattr(analytics, "generate_sales_forecasts", generate)
    monkeypatch.setattr(analytics, "summarize_forecasts",
                        lambda _db, records: SimpleNamespace(forecasts=records, total_products=len(records)))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(forecast_cache=None)))
    def run(history, limit):
        return analytics.generate_forecast(
            ForecastAnalyticsRequest(days_history=history, limit=limit),
            request=request, db=db_session, current_user=SimpleNamespace(id=1))
    assert len(run(60, 1).forecasts) == 1
    assert len(run(60, 3).forecasts) == 3
    assert calls == [60]
    assert len(run(90, 2).forecasts) == 2
    assert calls == [60, 90]
    request.app.state.forecast_cache["generated_at"] = datetime.now(UTC) - timedelta(minutes=31)
    assert len(run(90, 2).forecasts) == 2
    assert calls == [60, 90, 90]

def test_forecast_revenue_is_normalized_from_usd(client, db_session):
    from app.schemas import SalesForecast
    from app.services.forecasting_service import summarize_forecasts
    location, _ = seed_location_and_sales_profile(db_session)
    hnl = seed_product(client, location.id, sku="PROJ-HNL-001",
                       is_serialized=False, categoria="accesorio",
                       stock_inicial=1, costo=50, precio=100, moneda="Lps")
    usd = seed_product(client, location.id, sku="PROJ-USD-001",
                       is_serialized=False, categoria="accesorio",
                       stock_inicial=1, costo=50, precio=100, moneda="USD")
    records = [
        SalesForecast(product_id=product["id"], product_name="Forecast", current_stock=1,
                      average_daily_sales=1.0, predicted_sales_next_7_days=1,
                      predicted_sales_next_30_days=1, days_until_stockout=1,
                      restock_recommendation=0, confidence=.9, trend="stable")
        for product in (hnl, usd)
    ]
    report = summarize_forecasts(db_session, records)
    assert Decimal(str(report.estimated_revenue_7_days)) == Decimal("2600.00")
    assert Decimal(str(report.estimated_revenue_30_days)) == Decimal("2600.00")
