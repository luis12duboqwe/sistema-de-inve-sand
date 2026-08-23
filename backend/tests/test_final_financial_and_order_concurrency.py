import threading
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Order, OrderItem, Stock
from app.routers.order_state_integrity import cancel_order_canonical, update_order_canonical
from app.schemas import OrderUpdate

from .helpers import seed_location_and_sales_profile, seed_product


def _order_payload(sales_profile, location, product, *, phone: str) -> dict:
    return {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "tienda",
        "customer_name": "Cliente Final",
        "customer_phone": phone,
        "metodo_pago": "efectivo",
        "items": [
            {
                "product_id": product["id"],
                "cantidad": 1,
                "precio_unitario": 1000,
            }
        ],
    }


def _fake_superuser() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="final-integrity-test",
        email="final-integrity@test.local",
        is_active=True,
        is_superuser=True,
        role=None,
    )


def _set_lock_timeouts(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SET LOCAL lock_timeout = '5s'"))
        session.execute(text("SET LOCAL statement_timeout = '10s'"))


def test_order_edit_and_cancel_share_order_before_stock_lock_order(client, db_session) -> None:
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
        json=_order_payload(sales_profile, location, product, phone="71111111"),
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    outcomes: list[tuple[str, int]] = []
    user = _fake_superuser()

    update_payload = OrderUpdate.model_validate(
        {
            "items": [
                {
                    "product_id": product["id"],
                    "cantidad": 1,
                    "precio_unitario": 900,
                    "es_regalo_promocion": False,
                }
            ]
        }
    )

    def edit_worker() -> None:
        session: Session = SessionLocal()
        try:
            _set_lock_timeouts(session)
            barrier.wait()
            update_order_canonical(
                order_id=order_id,
                updates=update_payload,
                db=session,
                current_user=user,  # type: ignore[arg-type]
            )
            outcomes.append(("edit", 200))
        except HTTPException as exc:
            session.rollback()
            outcomes.append(("edit", exc.status_code))
        except BaseException as exc:
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    def cancel_worker() -> None:
        session: Session = SessionLocal()
        try:
            _set_lock_timeouts(session)
            barrier.wait()
            cancel_order_canonical(
                order_id=order_id,
                reason="Prueba edición vs cancelación",
                db=session,
                current_user=user,  # type: ignore[arg-type]
            )
            outcomes.append(("cancel", 200))
        except HTTPException as exc:
            session.rollback()
            outcomes.append(("cancel", exc.status_code))
        except BaseException as exc:
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    threads = [
        threading.Thread(target=edit_worker, daemon=True),
        threading.Thread(target=cancel_worker, daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads), "Edit/cancel concurrency test deadlocked"
    assert errors == []
    assert len(outcomes) == 2
    assert ("cancel", 200) in outcomes
    edit_status = next(status for name, status in outcomes if name == "edit")
    assert edit_status in {200, 400, 409}

    db_session.expire_all()
    final_order = db_session.query(Order).filter(Order.id == order_id).one()
    assert final_order.estado == "cancelada"
    final_stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product["id"], Stock.location_id == location.id)
        .one()
    )
    assert int(final_stock.cantidad_disponible or 0) == 2


def test_full_refund_never_exceeds_recorded_net_order_total(client, db_session) -> None:
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
        json=_order_payload(sales_profile, location, product, phone="72222222"),
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])
    completed = client.put(f"/api/orders/{order_id}/status", json={"estado": "completada"})
    assert completed.status_code == 200, completed.text

    # Simula el neto registrado tras una retoma/descuento: artículo bruto L1000,
    # pero sólo L200 quedan reconocidos como ingreso de la orden.
    db_session.execute(
        text("UPDATE orders SET total = :total WHERE id = :order_id"),
        {"total": Decimal("200.00"), "order_id": order_id},
    )
    db_session.commit()
    db_session.expire_all()

    returned = client.post(
        "/api/returns",
        json={
            "order_id": order_id,
            "reason": "Reembolso total de orden con neto reducido",
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

    today = __import__("datetime").date.today().isoformat()
    sales_response = client.get(f"/api/reports/sales?date_from={today}&date_to={today}")
    assert sales_response.status_code == 200, sales_response.text
    sales = sales_response.json()
    assert Decimal(str(sales["total_revenue"])) == Decimal("0.00")
    top = next(item for item in sales["top_products"] if item["product_id"] == product["id"])
    assert top["units_sold"] == 0
    assert Decimal(str(top["total_revenue"])) == Decimal("0.00")

    location_response = client.get(
        f"/api/reports/sales-summary-by-location?start_date={today}&end_date={today}"
    )
    assert location_response.status_code == 200, location_response.text
    location_row = next(row for row in location_response.json() if row["location_id"] == location.id)
    assert Decimal(str(location_row["total_ingresos"])) == Decimal("0.00")
    assert int(location_row["total_unidades_vendidas"]) == 0

    products_response = client.get(
        f"/api/reports/top-products-by-location/{location.id}?start_date={today}&end_date={today}"
    )
    assert products_response.status_code == 200, products_response.text
    product_row = next(row for row in products_response.json() if row["product_id"] == product["id"])
    assert Decimal(str(product_row["ingresos_totales"])) == Decimal("0.00")
    assert int(product_row["cantidad_vendida"]) == 0

    dashboard_response = client.get("/api/reports/dashboard")
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert Decimal(str(dashboard["total_revenue_today"])) >= Decimal("0.00")
    assert Decimal(str(dashboard["total_revenue_month"])) >= Decimal("0.00")


def test_dashboard_uses_product_cost_when_legacy_item_cost_is_null(client, db_session) -> None:
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
        json=_order_payload(sales_profile, location, product, phone="73333333"),
    )
    assert created.status_code == 201, created.text
    order_id = int(created.json()["id"])
    completed = client.put(f"/api/orders/{order_id}/status", json={"estado": "completada"})
    assert completed.status_code == 200, completed.text

    db_session.execute(
        text("UPDATE order_items SET costo_unitario = NULL WHERE order_id = :order_id"),
        {"order_id": order_id},
    )
    db_session.commit()
    db_session.expire_all()
    item = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).one()
    assert item.costo_unitario is None

    dashboard_response = client.get("/api/reports/dashboard")
    assert dashboard_response.status_code == 200, dashboard_response.text
    margin = Decimal(str(dashboard_response.json()["gross_margin_month"]))
    assert margin == Decimal("50.00")
