from .helpers import seed_location_and_sales_profile, seed_product


def _create_order(
    client,
    sales_profile_slug: str,
    location_id: int,
    product_id: int,
    customer_phone: str = "99999999",
    imei: str = "111111111111111",
):
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
                "imeis": [imei],
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
    imeis = ["111111111111111", "222222222222222", "333333333333333"]
    product = seed_product(
        client,
        location.id,
        stock_inicial=3,
        imei_values=imeis,
    )

    # Crear tres órdenes: una venta final, una cancelada y una pendiente.
    order_a = _create_order(
        client,
        sales_profile.slug,
        location.id,
        product["id"],
        customer_phone="88888888",
        imei=imeis[0],
    )
    order_b = _create_order(
        client,
        sales_profile.slug,
        location.id,
        product["id"],
        customer_phone="77777777",
        imei=imeis[1],
    )
    _create_order(
        client,
        sales_profile.slug,
        location.id,
        product["id"],
        customer_phone="66666666",
        imei=imeis[2],
    )

    complete_res = client.put(f"/api/orders/{order_a['id']}/status", json={"estado": "completada"})
    assert complete_res.status_code == 200, complete_res.text

    cancel_res = client.post(f"/api/orders/{order_b['id']}/cancel?reason=test")
    assert cancel_res.status_code == 200, cancel_res.text

    dash = client.get("/api/analytics/dashboard").json()

    # Solo una venta final debe contarse en el día.
    assert dash["total_orders_today"] == 1
    assert dash["total_revenue_today"] == 1000

    # Inventario usa costo (500) * stock disponible (1) -> 500.
    assert dash["total_inventory_value"] == 500


def test_analytics_forecast_endpoint_returns_summary(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    _create_order(client, sales_profile.slug, location.id, product["id"], customer_phone="77770000")

    payload = {
        "days_history": 60,
        "limit": 5,
        "product_ids": [product["id"]]
    }

    res = client.post("/api/analytics/forecast", json=payload)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["total_products"] >= 1
    assert data["estimated_revenue_7_days"] >= 0
    assert data["forecasts"], "Se esperaba al menos un pronóstico"
    assert data["forecasts"][0]["product_id"] == product["id"]


def test_analytics_forecast_filters_by_confidence(client, db_session):
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(client, location.id)

    _create_order(client, sales_profile.slug, location.id, product["id"], customer_phone="70000000")

    high_conf_payload = {
        "min_confidence": 0.9,
        "limit": 10
    }
    low_conf_payload = {
        "min_confidence": 0.0,
        "limit": 10
    }

    high_conf = client.post("/api/analytics/forecast", json=high_conf_payload).json()
    low_conf = client.post("/api/analytics/forecast", json=low_conf_payload).json()

    assert len(high_conf["forecasts"]) <= len(low_conf["forecasts"])
