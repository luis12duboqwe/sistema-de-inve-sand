import threading
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Return, Stock
from app.routers.returns import create_return
from app.schemas import ReturnCreate

from .helpers import seed_location_and_sales_profile, seed_product


def _create_paid_plus_gift_order(
    client: TestClient,
    db_session: Session,
    *,
    customer_name: str,
) -> tuple[dict, dict, object]:
    location, sales_profile = seed_location_and_sales_profile(db_session)
    product = seed_product(
        client,
        location.id,
        stock_inicial=4,
        is_serialized=False,
        categoria="accesorio",
    )

    created = client.post(
        "/api/orders",
        json={
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": customer_name,
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

    return order, product, location


def test_refund_and_store_credit_are_rejected_by_business_policy(
    client: TestClient,
    db_session: Session,
) -> None:
    order, product, _ = _create_paid_plus_gift_order(
        client,
        db_session,
        customer_name="Cliente Política Garantía",
    )

    for action in ("refund", "store_credit"):
        response = client.post(
            "/api/returns",
            json={
                "order_id": order["id"],
                "reason": "Acción no permitida por política comercial",
                "items": [
                    {
                        "product_id": product["id"],
                        "quantity": 1,
                        "condition": "nuevo",
                        "action": action,
                    }
                ],
            },
        )
        assert response.status_code == 422, response.text

    assert db_session.query(Return).count() == 0


def test_concurrent_warranty_returns_cannot_return_same_sold_units_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    order, product, location = _create_paid_plus_gift_order(
        client,
        db_session,
        customer_name="Cliente Garantía Concurrente",
    )

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = threading.Barrier(2)
    results: list[int] = []
    errors: list[BaseException] = []

    payload = ReturnCreate.model_validate(
        {
            "order_id": order["id"],
            "reason": "Competencia por las mismas unidades vendidas",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
                }
            ],
        }
    )
    fake_user = SimpleNamespace(
        id=1,
        username="concurrency-test",
        is_active=True,
        is_superuser=True,
        role=None,
    )

    def worker() -> None:
        session: Session = SessionLocal()
        try:
            barrier.wait()
            create_return(payload, db=session, current_user=fake_user)  # type: ignore[arg-type]
            results.append(201)
        except HTTPException as exc:
            session.rollback()
            results.append(exc.status_code)
        except BaseException as exc:  # surface unexpected thread failures to the test
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads), "Concurrent warranty return test deadlocked"
    assert errors == []
    assert sorted(results) == [201, 400]

    db_session.expire_all()
    assert db_session.query(Return).filter(Return.order_id == order["id"]).count() == 1
    stock = (
        db_session.query(Stock)
        .filter(
            Stock.product_id == product["id"],
            Stock.location_id == location.id,
        )
        .first()
    )
    assert stock is not None
    assert int(stock.cantidad_disponible or 0) == 0
    assert int(stock.cantidad_defectuosa or 0) == 2
