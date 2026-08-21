import threading
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Order, Return, Stock
from app.routers.order_state_integrity import (
    cancel_order_canonical,
    update_order_status_canonical,
)
from app.routers.returns import create_return
from app.schemas import OrderStatusUpdate, ReturnCreate

from .helpers import seed_location_and_sales_profile, seed_product


def _fake_superuser() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="concurrency-test",
        email="concurrency@test.local",
        is_active=True,
        is_superuser=True,
        role=None,
    )


def test_cancel_and_refund_are_serialized_without_double_restock(
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
            "customer_name": "Cliente Carrera Cancel Refund",
            "customer_phone": "75555555",
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

    db_session.expire_all()
    sold_stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product["id"], Stock.location_id == location.id)
        .one()
    )
    assert int(sold_stock.cantidad_disponible or 0) == 0

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = threading.Barrier(2)
    outcomes: list[tuple[str, int]] = []
    errors: list[BaseException] = []

    return_payload = ReturnCreate.model_validate(
        {
            "order_id": order["id"],
            "reason": "Carrera devolución vs cancelación",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "condition": "nuevo",
                    "action": "refund",
                }
            ],
        }
    )
    fake_user = _fake_superuser()

    def refund_worker() -> None:
        session: Session = SessionLocal()
        try:
            barrier.wait()
            create_return(return_payload, db=session, current_user=fake_user)  # type: ignore[arg-type]
            outcomes.append(("refund", 200))
        except HTTPException as exc:
            session.rollback()
            outcomes.append(("refund", exc.status_code))
        except BaseException as exc:
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    def cancel_worker() -> None:
        session: Session = SessionLocal()
        try:
            barrier.wait()
            cancel_order_canonical(
                order_id=order["id"],
                reason="Carrera devolución vs cancelación",
                db=session,
                current_user=fake_user,  # type: ignore[arg-type]
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

    threads = [threading.Thread(target=refund_worker), threading.Thread(target=cancel_worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads), "Cancel/refund concurrency test deadlocked"
    assert errors == []
    assert len(outcomes) == 2

    success_count = sum(1 for _, status in outcomes if status == 200)
    rejected = [status for _, status in outcomes if status != 200]
    assert success_count == 1
    assert len(rejected) == 1
    assert rejected[0] in {400, 409}

    db_session.expire_all()
    final_stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product["id"], Stock.location_id == location.id)
        .one()
    )
    assert int(final_stock.cantidad_disponible or 0) == 1

    final_order = db_session.query(Order).filter(Order.id == order["id"]).one()
    return_count = db_session.query(Return).filter(Return.order_id == order["id"]).count()
    if final_order.estado == "cancelada":
        assert return_count == 0
    else:
        assert final_order.estado in {"completada", "validada"}
        assert return_count == 1


def test_completion_and_cancellation_share_order_before_stock_lock_order(
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
            "customer_name": "Cliente Carrera Complete Cancel",
            "customer_phone": "75666666",
            "metodo_pago": "efectivo",
            "items": [{"product_id": product["id"], "cantidad": 1, "precio_unitario": 100}],
        },
    )
    assert created.status_code == 201, created.text
    order = created.json()

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = threading.Barrier(2)
    outcomes: list[tuple[str, int]] = []
    errors: list[BaseException] = []
    fake_user = _fake_superuser()
    completion_payload = OrderStatusUpdate.model_validate({"estado": "completada"})

    def complete_worker() -> None:
        session: Session = SessionLocal()
        try:
            barrier.wait()
            update_order_status_canonical(
                order_id=order["id"],
                payload=completion_payload,
                db=session,
                current_user=fake_user,  # type: ignore[arg-type]
            )
            outcomes.append(("complete", 200))
        except HTTPException as exc:
            session.rollback()
            outcomes.append(("complete", exc.status_code))
        except BaseException as exc:
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    def cancel_worker() -> None:
        session: Session = SessionLocal()
        try:
            barrier.wait()
            cancel_order_canonical(
                order_id=order["id"],
                reason="Carrera completar vs cancelar",
                db=session,
                current_user=fake_user,  # type: ignore[arg-type]
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

    threads = [threading.Thread(target=complete_worker), threading.Thread(target=cancel_worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads), "Complete/cancel concurrency test deadlocked"
    assert errors == []
    assert len(outcomes) == 2
    assert ("cancel", 200) in outcomes
    assert next(status for name, status in outcomes if name == "complete") in {200, 400, 409}

    db_session.expire_all()
    final_order = db_session.query(Order).filter(Order.id == order["id"]).one()
    assert final_order.estado == "cancelada"
    final_stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product["id"], Stock.location_id == location.id)
        .one()
    )
    assert int(final_stock.cantidad_disponible or 0) == 1
    assert int(final_stock.cantidad_reservada or 0) == 0


def test_runtime_cancel_rejects_order_with_existing_return(
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
            "customer_name": "Cliente Devolución Antes Cancelación",
            "customer_phone": "76666666",
            "metodo_pago": "efectivo",
            "items": [{"product_id": product["id"], "cantidad": 1, "precio_unitario": 100}],
        },
    )
    assert created.status_code == 201, created.text
    order = created.json()

    completed = client.put(f"/api/orders/{order['id']}/status", json={"estado": "completada"})
    assert completed.status_code == 200, completed.text

    returned = client.post(
        "/api/returns",
        json={
            "order_id": order["id"],
            "reason": "Devolución existente",
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

    canceled = client.post(f"/api/orders/{order['id']}/cancel?reason=No debe duplicar stock")
    assert canceled.status_code == 409, canceled.text
    assert "ya tiene devoluciones" in canceled.json()["detail"]

    db_session.expire_all()
    stock = (
        db_session.query(Stock)
        .filter(Stock.product_id == product["id"], Stock.location_id == location.id)
        .one()
    )
    assert int(stock.cantidad_disponible or 0) == 1

    super_admin_cancel = client.post(
        f"/api/super-admin/orders/{order['id']}/cancel",
        json={"reason": "No duplicar devolución existente"},
    )
    assert super_admin_cancel.status_code == 409, super_admin_cancel.text
    assert "ya tiene devoluciones" in super_admin_cancel.json()["detail"]

    db_session.expire_all()
    stock_after_super_admin = (
        db_session.query(Stock)
        .filter(Stock.product_id == product["id"], Stock.location_id == location.id)
        .one()
    )
    assert int(stock_after_super_admin.cantidad_disponible or 0) == 1
