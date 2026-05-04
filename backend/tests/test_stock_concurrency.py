import threading
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, TypedDict

from fastapi import HTTPException
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Location, Order, Product, Stock
from app.services.stock_transaction_helper import StockTransactionHelper
from app.utils.stock_manager import StockManager, StockValidationError
from postgres_test_utils import create_postgres_test_engine


class SaleItemDict(TypedDict):
    product_id: int
    cantidad: int


def _sale_item(product_id: int, cantidad: int) -> SaleItemDict:
    return {"product_id": product_id, "cantidad": cantidad}


def _require_pk(value: object, label: str) -> int:
    if not isinstance(value, int):
        raise AssertionError(f"{label} must be an int primary key")
    return value


def _optional_str(value: object, label: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise AssertionError(f"{label} must be a string or None")


def _int_value(value: object, label: str) -> int:
    if isinstance(value, int):
        return value
    raise AssertionError(f"{label} must be an int")


def _bootstrap_engine(tmp_path: Path, name: str):
    engine, _, cleanup = create_postgres_test_engine(name)
    Base.metadata.create_all(bind=engine)
    return engine, cleanup


def test_transfer_reservation_blocks_concurrent_order(tmp_path: Path) -> None:
    engine, cleanup = _bootstrap_engine(tmp_path, "stock_reservations")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    seed_session: Session = SessionLocal()
    try:
        location = Location(nombre="Tienda Norte", tipo="tienda", activo=True)
        product = Product(
            sku="SKU-CONCURRENT",
            nombre="Equipo QA",
            categoria="smartphones",
            marca="Marca",
            modelo="Modelo",
            condicion="nuevo",
            precio=Decimal("1500.00"),
            costo=Decimal("900.00"),
            moneda="HNL",
            garantia_meses=12,
            activo=True,
            is_serialized=False,
        )
        seed_session.add_all([location, product])
        seed_session.flush()
        stock = Stock(
            product_id=product.id,
            location_id=location.id,
            cantidad_disponible=5,
            cantidad_reservada=0,
        )
        seed_session.add(stock)
        seed_session.commit()
        loc_id = _require_pk(location.id, "location.id")
        product_id = _require_pk(product.id, "product.id")
    finally:
        seed_session.close()

    barrier = threading.Barrier(2)
    results: Dict[str, List[str | int]] = {"order": [], "transfer": []}

    def order_worker():
        session: Session = SessionLocal()
        helper = StockTransactionHelper(session)
        try:
            order = Order(
                customer_name="Cliente Concurrency",
                customer_phone="9999",
                canal="test",
                metodo_pago="efectivo",
                total=Decimal("0.00"),
                estado="pendiente",
                source_location_id=loc_id,
            )
            session.add(order)
            session.flush()
            payload: List[SaleItemDict] = [_sale_item(product_id=product_id, cantidad=3)]
            barrier.wait()
            batch = helper.prepare_sale_batch(
                items_payload=payload,
                location_id=loc_id,
                allow_pending_imei=False,
            )
            helper.persist_prepared_sale_items(
                db_order=order,
                prepared_items=batch.items,
                customer_name=_optional_str(order.customer_name, "order.customer_name"),
                canal=_optional_str(order.canal, "order.canal"),
                user_identifier="order-thread",
            )
            session.commit()
            results["order"].append("ok")
        except HTTPException as exc:
            session.rollback()
            results["order"].append(exc.status_code)
        finally:
            session.close()

    def transfer_worker():
        session: Session = SessionLocal()
        manager = StockManager(session)
        try:
            barrier.wait()
            _, stock_locked, _ = manager.validate_and_lock_stock(
                product_id=product_id,
                location_id=loc_id,
                quantity=3,
                operation_type="transfer_out",
            )
            manager.reserve_stock(
                stock=stock_locked,
                quantity=3,
                transfer_id=991,
                user_id="transfer-thread",
            )
            session.commit()
            results["transfer"].append("ok")
        except HTTPException as exc:
            session.rollback()
            results["transfer"].append(exc.status_code)
        except StockValidationError:
            session.rollback()
            results["transfer"].append("validation_error")
        finally:
            session.close()

    t1 = threading.Thread(target=order_worker)
    t2 = threading.Thread(target=transfer_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not ("ok" in results["order"] and "ok" in results["transfer"])
    assert "ok" in results["order"] or "ok" in results["transfer"]

    check_session: Session = SessionLocal()
    try:
        stock_row = check_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
        assert stock_row is not None
        disponible = _int_value(stock_row.cantidad_disponible, "stock.cantidad_disponible")
        reservada = _int_value(stock_row.cantidad_reservada, "stock.cantidad_reservada")
        assert disponible >= 0
        assert reservada >= 0
        assert reservada <= disponible
    finally:
        check_session.close()
        cleanup()


def test_release_reservation_allows_future_order(tmp_path: Path) -> None:
    engine, cleanup = _bootstrap_engine(tmp_path, "release_reservation")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    seed_session: Session = SessionLocal()
    try:
        location = Location(nombre="Warehouse", tipo="bodega", activo=True)
        product = Product(
            sku="SKU-REL",
            nombre="Equipo Demo",
            categoria="accesorio",
            marca="Marca",
            modelo="Modelo",
            condicion="nuevo",
            precio=Decimal("800.00"),
            costo=Decimal("500.00"),
            moneda="HNL",
            garantia_meses=6,
            activo=True,
            is_serialized=False,
        )
        seed_session.add_all([location, product])
        seed_session.flush()
        stock = Stock(
            product_id=product.id,
            location_id=location.id,
            cantidad_disponible=2,
            cantidad_reservada=0,
        )
        seed_session.add(stock)
        seed_session.commit()
        loc_id = _require_pk(location.id, "location.id")
        product_id = _require_pk(product.id, "product.id")
    finally:
        seed_session.close()

    reserve_session: Session = SessionLocal()
    try:
        manager = StockManager(reserve_session)
        _, stock_locked, _ = manager.validate_and_lock_stock(
            product_id=product_id,
            location_id=loc_id,
            quantity=2,
            operation_type="transfer_out",
        )
        manager.reserve_stock(
            stock=stock_locked,
            quantity=2,
            transfer_id=123,
            user_id="reservations",
        )
        reserve_session.commit()
    finally:
        reserve_session.close()

    release_session: Session = SessionLocal()
    try:
        manager = StockManager(release_session)
        stock_row = (
            release_session.query(Stock)
            .filter(Stock.product_id == product_id, Stock.location_id == loc_id)
            .with_for_update()
            .first()
        )
        assert stock_row is not None
        manager.release_reservation(
            stock=stock_row,
            quantity=2,
            transfer_id=123,
            is_rejection=True,
            user_id="reservations",
        )
        release_session.commit()
    finally:
        release_session.close()

    order_session: Session = SessionLocal()
    try:
        helper = StockTransactionHelper(order_session)
        order = Order(
            customer_name="Cliente Liberado",
            customer_phone="7777",
            canal="tienda",
            metodo_pago="tarjeta",
            total=Decimal("0.00"),
            estado="pendiente",
            source_location_id=loc_id,
        )
        order_session.add(order)
        order_session.flush()
        payload: List[SaleItemDict] = [_sale_item(product_id=product_id, cantidad=2)]
        batch = helper.prepare_sale_batch(
            items_payload=payload,
            location_id=loc_id,
            allow_pending_imei=False,
        )
        helper.persist_prepared_sale_items(
            db_order=order,
            prepared_items=batch.items,
            customer_name=_optional_str(order.customer_name, "order.customer_name"),
            canal=_optional_str(order.canal, "order.canal"),
            user_identifier="qa",
        )
        order_session.commit()
    finally:
        order_session.close()

    final_session: Session = SessionLocal()
    try:
        stock_row = final_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
        assert stock_row is not None
        assert _int_value(stock_row.cantidad_disponible, "stock.cantidad_disponible") == 0
        assert _int_value(stock_row.cantidad_reservada, "stock.cantidad_reservada") == 0
    finally:
        final_session.close()
        cleanup()
