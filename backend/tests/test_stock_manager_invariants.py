import threading

import pytest
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.database import Base
from app.models import Location, Product, Stock
from app.utils.stock_manager import StockManager, StockValidationError
from postgres_test_utils import create_postgres_test_engine


def _create_min_product(**overrides):
    data = {
        "sku": "SKU-1",
        "nombre": "Producto 1",
        "categoria": "accesorio",
        "marca": "Marca",
        "modelo": "Modelo",
        "capacidad": "",
        "condicion": "nuevo",
        "precio": 100,
        "costo": 0,
        "moneda": "HNL",
        "garantia_meses": 0,
        "activo": True,
        "is_serialized": False,
    }
    data.update(overrides)
    return Product(**data)


def _create_location(**overrides):
    data = {
        "nombre": "Tienda 1",
        "tipo": "tienda",
        "activo": True,
    }
    data.update(overrides)
    return Location(**data)


def test_validate_and_lock_stock_rejects_inconsistent_reserved(db_session):
    loc = _create_location()
    product = _create_min_product(sku="SKU-X")
    db_session.add_all([loc, product])
    db_session.flush()

    # reservado > disponible = inconsistencia
    stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=1, cantidad_reservada=2)
    db_session.add(stock)
    db_session.commit()

    manager = StockManager(db_session)

    with pytest.raises(HTTPException) as exc:
        manager.validate_and_lock_stock(product_id=product.id, location_id=loc.id, quantity=1)

    assert exc.value.status_code == 409


def test_decrease_stock_prevents_below_reserved(db_session):
    loc = _create_location(nombre="Tienda 2")
    product = _create_min_product(sku="SKU-Y")
    db_session.add_all([loc, product])
    db_session.flush()

    stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=5, cantidad_reservada=4)
    db_session.add(stock)
    db_session.flush()

    manager = StockManager(db_session)
    with pytest.raises(StockValidationError):
        manager.decrease_stock(stock=stock, quantity=2, operation_type="sale")


def test_reserve_stock_requires_positive_and_prevents_overreserve(db_session):
    loc = _create_location(nombre="Tienda 3")
    product = _create_min_product(sku="SKU-Z")
    db_session.add_all([loc, product])
    db_session.flush()

    stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=3, cantidad_reservada=0)
    db_session.add(stock)
    db_session.flush()

    manager = StockManager(db_session)

    with pytest.raises(StockValidationError):
        manager.reserve_stock(stock=stock, quantity=0, transfer_id=1)

    with pytest.raises(StockValidationError):
        manager.reserve_stock(stock=stock, quantity=4, transfer_id=1)


def test_release_reservation_requires_positive_and_no_over_release(db_session):
    loc = _create_location(nombre="Bodega")
    product = _create_min_product(sku="SKU-R")
    db_session.add_all([loc, product])
    db_session.flush()

    stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=10, cantidad_reservada=2)
    db_session.add(stock)
    db_session.flush()

    manager = StockManager(db_session)

    with pytest.raises(StockValidationError):
        manager.release_reservation(stock=stock, quantity=0, transfer_id=1)

    with pytest.raises(StockValidationError):
        manager.release_reservation(stock=stock, quantity=3, transfer_id=1)


def test_concurrent_double_decrement_never_leaves_negative(tmp_path):
    """Simula dos operaciones concurrentes que intentan decrementar el mismo stock.

    El CHECK constraint de cantidad_disponible >= 0 debe evitar que ambas
    transacciones confirmen dejando valores inválidos.
    """

    engine, _, cleanup = create_postgres_test_engine("stock_mgr_dec")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        Base.metadata.create_all(bind=engine)

        # Setup base data
        session = SessionLocal()
        loc = _create_location(nombre="Tienda C")
        product = _create_min_product(sku="SKU-C")
        session.add_all([loc, product])
        session.flush()
        stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=5, cantidad_reservada=0)
        session.add(stock)
        session.commit()
        loc_id, product_id = loc.id, product.id
    finally:
        session.close()

    barrier = threading.Barrier(2)
    unexpected_errors: list[Exception] = []
    outcomes: list[str] = []

    def worker():
        session = SessionLocal()
        manager = StockManager(session)
        try:
            # Both start at once; each must acquire the canonical pessimistic lock.
            barrier.wait(timeout=10)
            _product, locked_stock, _imeis = manager.validate_and_lock_stock(
                product_id=product_id, location_id=loc_id, quantity=4
            )
            manager.decrease_stock(stock=locked_stock, quantity=4, operation_type="sale")
            session.commit()
            outcomes.append("ok")
        except (HTTPException, StockValidationError):
            session.rollback()
            outcomes.append("rejected")
        except Exception as exc:
            session.rollback()
            unexpected_errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert all(not thread.is_alive() for thread in threads), "Stock writer deadlock"
    assert not unexpected_errors, [repr(exc) for exc in unexpected_errors]
    assert sorted(outcomes) == ["ok", "rejected"], outcomes

    check = SessionLocal()
    try:
        stock = check.query(Stock).filter(
            Stock.product_id == product_id, Stock.location_id == loc_id
        ).one()
        # A valid single decrement is 5 - 4 = 1. A lost update that allows
        # both writers to succeed would fail the outcomes assertion above.
        assert stock.cantidad_disponible == 1
        assert stock.cantidad_reservada == 0
    finally:
        check.close()
        cleanup()


def test_concurrent_reserve_does_not_overbook(tmp_path):
    """Dos reservas concurrentes no deben dejar reservado > disponible."""

    engine, _, cleanup = create_postgres_test_engine("stock_mgr_rsv")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        Base.metadata.create_all(bind=engine)

        session = SessionLocal()
        loc = _create_location(nombre="Tienda R")
        product = _create_min_product(sku="SKU-RSV")
        session.add_all([loc, product])
        session.flush()
        stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=5, cantidad_reservada=0)
        session.add(stock)
        session.commit()
        loc_id, product_id = loc.id, product.id
    finally:
        session.close()

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    unexpected_errors: list[Exception] = []

    def worker():
        session = SessionLocal()
        manager = StockManager(session)
        try:
            barrier.wait(timeout=10)
            _product, locked_stock, _imeis = manager.validate_and_lock_stock(
                product_id=product_id, location_id=loc_id,
                quantity=3, operation_type="transfer_out",
            )
            manager.reserve_stock(stock=locked_stock, quantity=3, transfer_id=42)
            session.commit()
            outcomes.append("ok")
        except (HTTPException, StockValidationError):
            session.rollback()
            outcomes.append("rejected")
        except Exception as exc:
            session.rollback()
            unexpected_errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert all(not thread.is_alive() for thread in threads), "Reservation deadlock"
    assert not unexpected_errors, [repr(exc) for exc in unexpected_errors]
    assert sorted(outcomes) == ["ok", "rejected"], outcomes

    check = SessionLocal()
    try:
        stock = check.query(Stock).filter(
            Stock.product_id == product_id, Stock.location_id == loc_id
        ).one()
        assert stock.cantidad_disponible == 5
        assert stock.cantidad_reservada == 3
    finally:
        check.close()
        cleanup()
