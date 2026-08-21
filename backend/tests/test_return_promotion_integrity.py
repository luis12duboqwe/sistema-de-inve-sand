from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Return

from .helpers import seed_location_and_sales_profile, seed_product


def test_cash_refund_cannot_include_promotional_gift_quantity(
    client: TestClient,
    db_session: Session,
) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=2,
        is_serialized=False,
        categoria="accesorio",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente Promo",
            "customer_phone": "73333333",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                    "precio_unitario": 100,
                },
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                    "precio_unitario": 100,
                    "es_regalo_promocion": True,
                },
            ],
        },
    )
    assert created.status_code == 201, created.text
    order = created.json()
    assert Decimal(str(order["total"])) == Decimal("100.00")

    completed = client.put(
        f"/api/orders/{order['id']}/status",
        json={"estado": "completada"},
    )
    assert completed.status_code == 200, completed.text

    invalid_refund = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "reason": "No debe reembolsar el regalo",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                    "condition": "nuevo",
                    "action": "refund",
                }
            ],
        },
    )
    assert invalid_refund.status_code == 400, invalid_refund.text
    assert "excede las unidades pagadas" in invalid_refund.json()["detail"]
    assert db_session.query(Return).count() == 0

    valid_refund = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "reason": "Reembolso de la unidad pagada",
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
    assert valid_refund.status_code == 201, valid_refund.text

    report_response = client.get("/api/reports/sales")
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert Decimal(str(report["total_revenue"])) == Decimal("0.00")
    top = next(item for item in report["top_products"] if item["product_id"] == product["id"])
    assert top["units_sold"] == 0
    assert Decimal(str(top["total_revenue"])) == Decimal("0.00")
