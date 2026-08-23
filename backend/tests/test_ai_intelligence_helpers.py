from datetime import UTC, datetime, timedelta, timezone

from app.services.ai_intelligence_helpers import (
    build_fallback_recommendations,
    ensure_aware_utc,
    isoformat_optional,
    parse_ai_business_response,
    safe_float,
)


def test_safe_float_and_optional_datetime_normalization():
    assert safe_float(None) == 0.0
    assert safe_float("12.5") == 12.5
    assert safe_float("not-a-number") == 0.0
    assert isoformat_optional(None) is None

    naive = datetime(2026, 8, 23, 12, 30)
    aware = ensure_aware_utc(naive)
    assert aware is not None
    assert aware.tzinfo == UTC
    assert isoformat_optional(aware) == aware.isoformat()

    honduras_time = datetime(2026, 8, 23, 6, 30, tzinfo=timezone(-timedelta(hours=6)))
    normalized = ensure_aware_utc(honduras_time)
    assert normalized == datetime(2026, 8, 23, 12, 30, tzinfo=UTC)


def test_parse_ai_business_response_preserves_historical_json_semantics():
    assert parse_ai_business_response('{"summary":"ok"}') == {"summary": "ok"}
    assert parse_ai_business_response('texto antes {"summary":"ok"} texto después') == {"summary": "ok"}
    assert parse_ai_business_response("[1, 2, 3]") == [1, 2, 3]
    assert parse_ai_business_response("") == {}
    assert parse_ai_business_response("no json here") == {}


def test_fallback_recommendations_cover_stock_slow_mover_and_top_seller():
    recommendations = build_fallback_recommendations(
        {
            "stock_alerts": [
                {"product_name": "iPhone 15", "stock_available": 2, "days_until_stockout": "3.4"}
            ],
            "slow_movers": [
                {"product_name": "Cable X", "stock_available": 20, "days_without_sales": 45}
            ],
            "top_sellers": [
                {"product_name": "iPhone 14", "revenue": "25000.50", "gross_profit": "4800.25"}
            ],
        }
    )

    assert [item.category for item in recommendations] == ["inventario", "ventas", "crecimiento"]
    assert recommendations[0].priority == "alta"
    assert "iPhone 15" in recommendations[0].action
    assert "Cable X" in recommendations[1].action
    assert "iPhone 14" in recommendations[2].action


def test_fallback_recommendations_return_operational_default_without_metrics():
    recommendations = build_fallback_recommendations({})

    assert len(recommendations) == 1
    assert recommendations[0].title == "Revisar estrategia"
    assert recommendations[0].category == "operaciones"
