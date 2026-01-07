import threading
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Location, Order, Product, ProductIMEI, Stock
from app.services.stock_transaction_helper import StockTransactionHelper


def _create_location(**overrides):
    data = {
        "nombre": "Tienda QA",
        "tipo": "tienda",
        "activo": True,
    }
    data.update(overrides)
    return Location(**data)


def _create_product(**overrides):
    data = {
        "sku": "SKU-HELPER",
        "nombre": "Producto QA",
        "categoria": "accesorio",
        "marca": "Marca",
        "modelo": "Modelo",
        "capacidad": "128GB",
        "condicion": "nuevo",
        "precio": Decimal("10000.00"),
        "costo": Decimal("5000.00"),
        "moneda": "HNL",
        "garantia_meses": 12,
        "activo": True,
        "is_serialized": False,
    }
    data.update(overrides)
    return Product(**data)


def test_prepare_sale_batch_counts_gifts(db_session):
    loc = _create_location(nombre="Tienda Docs")
    product = _create_product()
    db_session.add_all([loc, product])
    db_session.flush()

    stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=5, cantidad_reservada=0)
    db_session.add(stock)
    db_session.commit()

    helper = StockTransactionHelper(db_session)
    payload = [
        {"product_id": product.id, "cantidad": 1, "precio_unitario": "12000", "es_regalo_promocion": False},
        {"product_id": product.id, "cantidad": 1, "precio_unitario": "5000", "es_regalo_promocion": True},
    ]

    result = helper.prepare_sale_batch(items_payload=payload, location_id=loc.id, allow_pending_imei=False)

    assert result.total == Decimal("12000")
    assert result.gifts_total == Decimal("5000")
    assert result.has_items is True
    assert result.has_regular_items is True


def _bootstrap_engine(tmp_path, name):
    db_path = tmp_path / name
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    with engine.connect() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
        connection.execute(text("PRAGMA synchronous=NORMAL"))
    return engine


def test_concurrent_sales_do_not_overdraw_stock(tmp_path):
    engine = _bootstrap_engine(tmp_path, "helper_concurrency.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    try:
        loc = _create_location(nombre="Tienda Concurrency")
        product = _create_product(sku="SKU-CONC", precio=Decimal("2000"))
        session.add_all([loc, product])
        session.flush()
        stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=5, cantidad_reservada=0)
        session.add(stock)
        session.commit()
        loc_id, product_id = loc.id, product.id
    finally:
        session.close()

    order_ids = []
    session = SessionLocal()
    try:
        for label in ("A", "B"):
            order = Order(
                customer_name=f"Cliente {label}",
                customer_phone="9999",
                canal="test",
                metodo_pago="efectivo",
                total=Decimal("0"),
                estado="pendiente",
                source_location_id=loc_id,
            )
            session.add(order)
            session.flush()
            order_ids.append(order.id)
        session.commit()
    finally:
        session.close()

    barrier = threading.Barrier(2)
    successes = []
    errors = []

    def worker(worker_label, order_id):
        s = SessionLocal()
        helper = StockTransactionHelper(s)
        try:
            order = s.get(Order, order_id)
            if order is None:
                errors.append(500)
                return

            payload = [{"product_id": product_id, "cantidad": 3}]
            barrier.wait()
            batch = helper.prepare_sale_batch(
                items_payload=payload,
                location_id=loc_id,
                allow_pending_imei=False,
            )
            order.total = batch.total
            helper.persist_prepared_sale_items(
                db_order=order,
                prepared_items=batch.items,
                customer_name=order.customer_name,
                canal=order.canal,
                user_identifier=f"tester-{worker_label}",
            )
            s.commit()
            successes.append(order.id)
        except HTTPException as exc:  # Esperamos que una transacción falle por stock insuficiente
            s.rollback()
            errors.append(exc.status_code)
        finally:
            s.close()

    t1 = threading.Thread(target=worker, args=("A", order_ids[0]))
    t2 = threading.Thread(target=worker, args=("B", order_ids[1]))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(successes) == 1
    assert len(errors) == 1
    assert errors[0] == 409

    check_session = SessionLocal()
    try:
        final_stock = check_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == loc_id).first()
        assert final_stock is not None
        assert final_stock.cantidad_disponible >= 0
        assert final_stock.cantidad_reservada == 0
    finally:
        check_session.close()


def test_concurrent_serialized_sales_only_one_succeeds(tmp_path):
    engine = _bootstrap_engine(tmp_path, "helper_serialized.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    try:
        loc = _create_location(nombre="Tienda IMEI")
        product = _create_product(sku="SKU-IMEI", is_serialized=True)
        session.add_all([loc, product])
        session.flush()
        stock = Stock(product_id=product.id, location_id=loc.id, cantidad_disponible=1, cantidad_reservada=0)
        session.add(stock)
        imei_record = ProductIMEI(
            product_id=product.id,
            location_id=loc.id,
            imei="123456789012345",
            vendido=False,
        )
        session.add(imei_record)
        session.commit()
        loc_id, product_id = loc.id, product.id
        imei_value = imei_record.imei
    finally:
        session.close()

    order_ids = []
    session = SessionLocal()
    try:
        for label in ("X", "Y"):
            order = Order(
                customer_name=f"Cliente {label}",
                customer_phone="8888",
                canal="test",
                metodo_pago="efectivo",
                total=Decimal("0"),
                estado="pendiente",
                source_location_id=loc_id,
            )
            session.add(order)
            session.flush()
            order_ids.append(order.id)
        session.commit()
    finally:
        session.close()

    barrier = threading.Barrier(2)
    success_flags = []
    failures = []

    def worker(prefix, order_id):
        s = SessionLocal()
        helper = StockTransactionHelper(s)
        try:
            order = s.get(Order, order_id)
            if order is None:
                failures.append(500)
                return

            payload = [{"product_id": product_id, "cantidad": 1, "imeis": [imei_value]}]
            barrier.wait()
            batch = helper.prepare_sale_batch(
                items_payload=payload,
                location_id=loc_id,
                allow_pending_imei=False,
            )
            order.total = batch.total
            helper.persist_prepared_sale_items(
                db_order=order,
                prepared_items=batch.items,
                customer_name=order.customer_name,
                canal=order.canal,
                user_identifier=f"tester-{prefix}",
            )
            s.commit()
            success_flags.append(order.id)
        except HTTPException as exc:
            s.rollback()
            failures.append(exc.status_code)
        finally:
            s.close()

    t1 = threading.Thread(target=worker, args=("X", order_ids[0]))
    t2 = threading.Thread(target=worker, args=("Y", order_ids[1]))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(success_flags) == 1
    assert len(failures) == 1
    assert failures[0] in {400, 409}

    check_session = SessionLocal()
    try:
        final_imei = check_session.query(ProductIMEI).filter(ProductIMEI.product_id == product_id).first()
        assert final_imei is not None
        assert final_imei.vendido is True
    finally:
        check_session.close()
