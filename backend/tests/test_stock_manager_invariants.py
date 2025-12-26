import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.database import Base
from app.models import Location, Product, Stock
from app.utils.stock_manager import StockManager, StockValidationError


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

    Nota: SQLite no respeta SELECT..FOR UPDATE, pero el CHECK constraint de
    cantidad_disponible >= 0 debe evitar que ambas transacciones confirmen dejando negativo.
    """

    db_path = tmp_path / "concurrency.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    # Setup base data
    session = SessionLocal()
    try:
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
    errors = []

    def worker():
        s = SessionLocal()
        try:
            st = s.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
            barrier.wait()
            st.cantidad_disponible -= 4
            s.flush()
            s.commit()
        except Exception as e:  # noqa: BLE001
            s.rollback()
            errors.append(e)
        finally:
            s.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Stock final nunca debe ser negativo ni violar invariantes
    s = SessionLocal()
    try:
        final = s.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
        assert final is not None
        assert final.cantidad_disponible >= 0
        assert final.cantidad_reservada >= 0
        assert final.cantidad_reservada <= final.cantidad_disponible
    finally:
        s.close()


def test_concurrent_reserve_does_not_overbook(tmp_path):
    """Dos reservas concurrentes no deben dejar reservado > disponible."""

    db_path = tmp_path / "reserve.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
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
    errors = []

    def worker(qty):
        s = SessionLocal()
        mgr = StockManager(s)
        try:
            st = s.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
            barrier.wait()
            mgr.reserve_stock(stock=st, quantity=qty, transfer_id=42)
            s.commit()
        except Exception as e:  # noqa: BLE001
            s.rollback()
            errors.append(e)
        finally:
            s.close()

    t1 = threading.Thread(target=worker, args=(3,))
    t2 = threading.Thread(target=worker, args=(3,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    s = SessionLocal()
    try:
        final = s.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
        assert final is not None
        assert final.cantidad_reservada <= final.cantidad_disponible
        assert final.cantidad_disponible >= 0
    finally:
        s.close()
