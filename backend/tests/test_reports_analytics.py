from .helpers import seed_location_and_sales_profile, seed_product


def _create_order(client, sales_profile_slug: str, location_id: int, product_id: int, customer_phone: str = "99999999"):
    order_payload = {
        "sales_profile_slug": sales_profile_slug,
        "source_location_id": location_id,
        "canal": "whatsapp",
        "customer_name": "Cliente Test",
        "customer_phone": customer_phone,
        "metodo_pago": "efectivo",
        "items": [
            {
                "product_id": product_id,
                "cantidad": 1,
                "imeis": ["111111111111111"],
                "precio_unitario": 1000,
            }
        ],
    }
    res = client.post("/api/orders", json=order_payload)
    assert res.status_code == 201, res.text
    return res.json()


def test_reports_dashboard_rejects_unknown_location(client, db_session):
    # No crear ubicación con ese ID
    res = client.get("/api/reports/dashboard?location_id=9999")
    assert res.status_code == 404


def test_analytics_dashboard_excludes_cancelled_orders(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    # Crear dos órdenes: una quedará cancelada
    order_a = _create_order(client, sales_profile.slug, location.id, product["id"], customer_phone="88888888")
    order_b = _create_order(client, sales_profile.slug, location.id, product["id"], customer_phone="77777777")

    cancel_res = client.post(f"/api/orders/{order_b['id']}/cancel?reason=test")
    assert cancel_res.status_code == 200, cancel_res.text

    dash = client.get("/api/analytics/dashboard").json()

    # Solo una orden no cancelada debe contarse en el día
    assert dash["total_orders_today"] == 1
    assert dash["total_revenue_today"] == 1000

    # Inventario usa costo (500) * stock disponible (1) -> 500
    assert dash["total_inventory_value"] == 500
