from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event, Lock, get_ident
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, Stock, StockHistory, StockTransfer
from app.routers import products, super_admin, super_admin_integrity
from app.routers.stock_transfer_integrity import confirm_transfer_integrity
from app.schemas import ProductRestockRequest, StockTransferConfirm


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="purge-lock-compat",
        is_superuser=True,
        is_active=True,
        role=None,
    )


def _normalized(statement: str) -> str:
    return " ".join(statement.upper().split())


def _product_and_locations(db_session: Session, *, two_locations: bool = False):
    suffix = uuid4().hex
    product = Product(
        sku=f"PURGE-LOCK-{suffix}",
        nombre=f"Producto Purge Lock {suffix}",
        categoria="accesorio",
        marca="Marca QA",
        modelo=f"Modelo-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("500.00"),
        costo=Decimal("50.00"),
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    source = Location(nombre=f"Origen Purge {suffix}", tipo="tienda", activo=True)
    rows = [product, source]
    destination = None
    if two_locations:
        destination = Location(nombre=f"Destino Purge {suffix}", tipo="tienda", activo=True)
        rows.append(destination)
    db_session.add_all(rows)
    db_session.flush()
    return product, source, destination


def _session_factory(db_session: Session):
    bind = db_session.get_bind()
    return bind, sessionmaker(autocommit=False, autoflush=False, bind=bind)


def _purge(session, product_id: int) -> tuple[int, str]:
    try:
        result = super_admin.purge_product_for_admin(
            product_id,
            super_admin.ProductPurgeRequest(reason="Prueba concurrente de purga fail-fast"),
            session,
            _user(),
        )
        return 200, str(result["ok"])
    except Exception as exc:  # noqa: BLE001 - regression captures lock contention
        session.rollback()
        return int(getattr(exc, "status_code", 500)), repr(exc)


def test_purge_fails_fast_when_restock_holds_product(db_session: Session) -> None:
    product, location, _ = _product_and_locations(db_session)
    product_id = int(product.id)
    location_id = int(location.id)
    db_session.add(Stock(product_id=product_id, location_id=location_id, cantidad_disponible=10))
    db_session.commit()

    bind, SessionLocal = _session_factory(db_session)
    state_lock = Lock()
    roles: dict[int, str] = {}
    restock_product_locked = Event()
    purge_finished = Event()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        with state_lock:
            role = roles.get(get_ident())
        if (
            role == "restock"
            and normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "FOR NO KEY UPDATE" in normalized
        ):
            restock_product_locked.set()
            purge_finished.wait(timeout=10)

    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    def run_restock():
        session = SessionLocal()
        with state_lock:
            roles[get_ident()] = "restock"
        try:
            result = products.restock_product(
                product_id,
                ProductRestockRequest(location_id=location_id, cantidad=2, costo_unitario=Decimal("100.00")),
                session,
                _user(),
            )
            return 200, str(result.costo)
        finally:
            with state_lock:
                roles.pop(get_ident(), None)
            session.close()

    def run_purge():
        session = SessionLocal()
        try:
            assert restock_product_locked.wait(timeout=10)
            return _purge(session, product_id)
        finally:
            purge_finished.set()
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            restock_future = pool.submit(run_restock)
            purge_future = pool.submit(run_purge)
            restock_result = restock_future.result(timeout=20)
            purge_result = purge_future.result(timeout=20)
    finally:
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert restock_result[0] == 200
    assert purge_result[0] == 409
    db_session.expire_all()
    persisted = db_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == location_id).one()
    assert persisted.cantidad_disponible == 12
    assert db_session.get(Product, product_id) is not None


def test_purge_fails_fast_when_adjustment_holds_stock(db_session: Session) -> None:
    product, location, _ = _product_and_locations(db_session)
    product_id = int(product.id)
    location_id = int(location.id)
    db_session.add(Stock(product_id=product_id, location_id=location_id, cantidad_disponible=10))
    db_session.commit()

    bind, SessionLocal = _session_factory(db_session)
    state_lock = Lock()
    roles: dict[int, str] = {}
    adjustment_stock_locked = Event()
    purge_finished = Event()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        with state_lock:
            role = roles.get(get_ident())
        if (
            role == "adjust"
            and normalized.startswith("SELECT")
            and "FROM STOCK " in normalized
            and "FOR UPDATE" in normalized
        ):
            adjustment_stock_locked.set()
            purge_finished.wait(timeout=10)

    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    def run_adjustment():
        session = SessionLocal()
        with state_lock:
            roles[get_ident()] = "adjust"
        try:
            result = super_admin_integrity.adjust_stock_integrity(
                super_admin.StockAdjustmentRequest(
                    product_id=product_id,
                    location_id=location_id,
                    cantidad_disponible=18,
                    cantidad_reservada=0,
                    cantidad_defectuosa=0,
                    reason="Ajuste concurrente para prueba",
                ),
                session,
                _user(),
            )
            return 200, str(result["cantidad_disponible"])
        finally:
            with state_lock:
                roles.pop(get_ident(), None)
            session.close()

    def run_purge():
        session = SessionLocal()
        try:
            assert adjustment_stock_locked.wait(timeout=10)
            return _purge(session, product_id)
        finally:
            purge_finished.set()
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            adjust_future = pool.submit(run_adjustment)
            purge_future = pool.submit(run_purge)
            adjust_result = adjust_future.result(timeout=20)
            purge_result = purge_future.result(timeout=20)
    finally:
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert adjust_result[0] == 200
    assert purge_result[0] == 409
    db_session.expire_all()
    stock = db_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == location_id).one()
    assert stock.cantidad_disponible == 18
    assert db_session.query(StockHistory).filter(
        StockHistory.product_id == product_id,
        StockHistory.tipo_cambio == "super_admin_adjustment",
    ).count() == 1


def test_purge_fails_fast_when_transfer_transition_holds_transfer(db_session: Session) -> None:
    product, source, destination = _product_and_locations(db_session, two_locations=True)
    assert destination is not None
    product_id = int(product.id)
    source_id = int(source.id)
    destination_id = int(destination.id)
    db_session.add_all([
        Stock(product_id=product_id, location_id=source_id, cantidad_disponible=10, cantidad_reservada=3),
        Stock(product_id=product_id, location_id=destination_id, cantidad_disponible=5),
    ])
    transfer = StockTransfer(
        product_id=product_id,
        from_location_id=source_id,
        to_location_id=destination_id,
        cantidad=3,
        estado="pendiente",
        created_by="purge-lock-compat",
    )
    db_session.add(transfer)
    db_session.commit()
    transfer_id = int(transfer.id)

    bind, SessionLocal = _session_factory(db_session)
    state_lock = Lock()
    roles: dict[int, str] = {}
    transfer_locked = Event()
    purge_finished = Event()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        with state_lock:
            role = roles.get(get_ident())
        if (
            role == "confirm"
            and normalized.startswith("SELECT")
            and "FROM STOCK_TRANSFERS" in normalized
            and "FOR UPDATE" in normalized
        ):
            transfer_locked.set()
            purge_finished.wait(timeout=10)

    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    def run_confirmation():
        session = SessionLocal()
        with state_lock:
            roles[get_ident()] = "confirm"
        try:
            result = confirm_transfer_integrity(
                transfer_id,
                StockTransferConfirm(received_quantity=3),
                db=session,
                current_user=_user(),
            )
            return 200, str(result.estado)
        finally:
            with state_lock:
                roles.pop(get_ident(), None)
            session.close()

    def run_purge():
        session = SessionLocal()
        try:
            assert transfer_locked.wait(timeout=10)
            return _purge(session, product_id)
        finally:
            purge_finished.set()
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            confirm_future = pool.submit(run_confirmation)
            purge_future = pool.submit(run_purge)
            confirm_result = confirm_future.result(timeout=20)
            purge_result = purge_future.result(timeout=20)
    finally:
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert confirm_result[0] == 200
    assert purge_result[0] == 409
    db_session.expire_all()
    persisted_transfer = db_session.get(StockTransfer, transfer_id)
    assert persisted_transfer is not None
    assert persisted_transfer.estado == "confirmada"
    source_stock = db_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == source_id).one()
    destination_stock = db_session.query(Stock).filter(Stock.product_id == product_id, Stock.location_id == destination_id).one()
    assert source_stock.cantidad_disponible == 7
    assert source_stock.cantidad_reservada == 0
    assert destination_stock.cantidad_disponible == 8
