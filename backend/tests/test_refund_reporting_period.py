from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Order

from .helpers import seed_location_and_sales_profile, seed_product


def test_refund_does_not_make_current_period_negative_for_old_sale(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=1,
        is_serialized=False,
        categoria="accesorio",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente Histórico",
            "customer_phone": "74444444",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                    "precio_unitario": 100,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    order = created.json()

    completed = client.put(
        f"/api/orders/{order['id']}/status",
        json={"estado": "completada"},
    )
    assert completed.status_code == 200, completed.text

    old_sale_date = date.today() - timedelta(days=60)
    order_row = db_session.query(Order).filter(Order.id == order["id"]).one()
    order_row.completed_at = datetime.combine(old_sale_date, time(hour=12))
    db_session.commit()

    returned = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "reason": "Devolución posterior de venta histórica",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "condition": "nuevo",
                    "action": "refund",
                }
            ],
        },
    )
    assert returned.status_code == 201, returned.text

    today = date.today().isoformat()
    today_report_response = client.get(
        f"/api/reports/sales?date_from={today}&date_to={today}"
    )
    assert today_report_response.status_code == 200, today_report_response.text
    today_report = today_report_response.json()
    assert today_report["total_orders"] == 0
    assert Decimal(str(today_report["total_revenue"])) == Decimal("0.00")
    assert today_report["top_products"] == []

    today_location_response = client.get(
        f"/api/reports/sales-summary-by-location?start_date={today}&end_date={today}"
    )
    assert today_location_response.status_code == 200, today_location_response.text
    assert today_location_response.json() == []

    today_products_response = client.get(
        f"/api/reports/top-products-by-location/{location.id}?start_date={today}&end_date={today}"
    )
    assert today_products_response.status_code == 200, today_products_response.text
    assert today_products_response.json() == []

    dashboard_response = client.get("/api/reports/dashboard")
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert Decimal(str(dashboard["total_revenue_today"])) >= Decimal("0.00")
    assert Decimal(str(dashboard["total_revenue_month"])) >= Decimal("0.00")

    old_day = old_sale_date.isoformat()
    historical_response = client.get(
        f"/api/reports/sales?date_from={old_day}&date_to={old_day}"
    )
    assert historical_response.status_code == 200, historical_response.text
    historical = historical_response.json()
    assert historical["total_orders"] == 1
    assert Decimal(str(historical["total_revenue"])) == Decimal("0.00")
    top = next(item for item in historical["top_products"] if item["product_id"] == product["id"])
    assert top["units_sold"] == 0
    assert Decimal(str(top["total_revenue"])) == Decimal("0.00")
