import threading
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Order, SystemConfig
from app.routers.daily_close import validate_daily_close
from app.schemas.daily_close import DailyCloseValidateRequest
from app.utils.daily_close_code import DAILY_CLOSE_CODE_KEY, hash_daily_close_code

from .helpers import seed_location_and_sales_profile, seed_product


def _plain_order_payload(sales_profile, location, product, *, phone: str) -> dict:
    return {
        "sales_profile_slug": sales_profile.slug,
        "source_location_id": location.id,
        "canal": "tienda",
        "customer_name": "Cliente Integridad Final",
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


def test_super_admin_stock_adjust_rejects_missing_location(client, db_session) -> None:
    location, _ = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=1,
        is_serialized=False,
        categoria="accesorio",
    )

    response = client.post(
        "/api/super-admin/stock/adjust",
        json={
            "reason": "Ubicación inexistente de prueba",
            "product_id": product["id"],
            "location_id": 999999,
            "cantidad_disponible": 1,
            "cantidad_reservada": 0,
            "cantidad_defectuosa": 0,
        },
    )

    assert response.status_code == 404, response.text
    assert "Ubicación" in response.json().get("detail", "")


def test_payment_breakdown_rejects_exact_one_cent_difference(client, db_session) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=1,
        is_serialized=False,
        categoria="accesorio",
    )
    payload = _plain_order_payload(sales_profile, location, product, phone="78888888")
    payload["payment_breakdown"] = [
        {"method": "efectivo", "amount": 999.99},
    ]

    response = client.post("/api/orders", json=payload)

    assert response.status_code == 400, response.text
    assert "desglose de pagos" in response.json().get("detail", "")
    db_session.expire_all()
    assert db_session.query(Order).filter(Order.customer_phone == "78888888").count() == 0


def test_daily_close_overlapping_reversed_ids_do_not_deadlock(client, db_session) -> None:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    location_id = int(location.id)
    product = seed_product(
        client,
        location_id,
        stock_inicial=2,
        is_serialized=False,
        categoria="accesorio",
    )

    order_ids: list[int] = []
    for phone in ("79999991", "79999992"):
        created = client.post(
            "/api/orders",
            json=_plain_order_payload(sales_profile, location, product, phone=phone),
        )
        assert created.status_code == 201, created.text
        order_id = int(created.json()["id"])
        completed = client.put(
            f"/api/orders/{order_id}/status",
            json={"estado": "completada"},
        )
        assert completed.status_code == 200, completed.text
        order_ids.append(order_id)

    validation_code = "24682468"
    db_session.add(
        SystemConfig(
            key=DAILY_CLOSE_CODE_KEY,
            value=hash_daily_close_code(validation_code),
            description="Código cierre prueba concurrencia",
            updated_by="test",
        )
    )
    db_session.commit()

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    results: list[list[int]] = []
    fake_user = SimpleNamespace(
        id=1,
        username="daily-close-concurrency",
        is_active=True,
        is_superuser=True,
        role=None,
    )

    def worker(ids: list[int]) -> None:
        session: Session = SessionLocal()
        try:
            # Use only primitive values inside worker threads. SQLAlchemy expires ORM
            # instances on commit; dereferencing a shared fixture object here would
            # refresh it through the parent Session concurrently and test the fixture
            # rather than the application's row-lock ordering.
            payload = DailyCloseValidateRequest(
                validation_code=validation_code,
                order_ids=ids,
                location_id=location_id,
                notas="Prueba de orden de locks",
            )

            # Synchronize before either worker checks out a DB connection.
            barrier.wait(timeout=5)

            # The regression must never be able to hang CI indefinitely. PostgreSQL
            # will turn an unexpected row-lock wait into a prompt test failure.
            if session.get_bind().dialect.name == "postgresql":
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
                session.execute(text("SET LOCAL statement_timeout = '10s'"))

            response = validate_daily_close(
                payload,
                db=session,
                current_user=fake_user,  # type: ignore[arg-type]
            )
            results.append(list(response.validated_orders))
        except HTTPException as exc:
            session.rollback()
            errors.append(exc)
        except BaseException as exc:
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    threads = [
        threading.Thread(target=worker, args=([order_ids[0], order_ids[1]],), daemon=True),
        threading.Thread(target=worker, args=([order_ids[1], order_ids[0]],), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads), "Daily close concurrency test deadlocked"
    assert errors == []
    assert len(results) == 2

    db_session.expire_all()
    stored_orders = (
        db_session.query(Order)
        .filter(Order.id.in_(order_ids))
        .order_by(Order.id.asc())
        .all()
    )
    assert len(stored_orders) == 2
    assert all(order.estado == "validada" for order in stored_orders)
    assert all(order.validada_at is not None for order in stored_orders)
