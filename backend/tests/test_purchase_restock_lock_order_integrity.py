from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Event, Lock, get_ident
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, PurchaseReceipt, Stock, StockHistory
from app.routers import multistore_control, products
from app.schemas import ProductRestockRequest
from app.schemas.control import PurchaseReceiptCreate, PurchaseReceiptItemCreate


def _seed_product(
    db_session: Session,
    *,
    location: Location | None = None,
    initial_stock: int = 10,
    initial_cost: Decimal = Decimal("100.00"),
) -> tuple[int, int]:
    suffix = uuid4().hex
    if location is None:
        location = Location(
            nombre=f"Tienda Lock Order {suffix}",
            tipo="tienda",
            activo=True,
        )
        db_session.add(location)
        db_session.flush()

    product = Product(
        sku=f"LOCK-{suffix}",
        nombre=f"Producto Lock {suffix}",
        categoria="accesorio",
        marca="Marca QA",
        modelo=f"Modelo-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=initial_cost,
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    db_session.add(product)
    db_session.flush()
    db_session.add(
        Stock(
            product_id=product.id,
            location_id=location.id,
            cantidad_disponible=initial_stock,
            cantidad_reservada=0,
            cantidad_defectuosa=0,
        )
    )
    db_session.commit()
    return int(product.id), int(location.id)


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="lock-order-concurrency",
        is_superuser=True,
        role=None,
    )


def _normalized(statement: str) -> str:
    return " ".join(statement.upper().split())


def test_manual_restock_and_purchase_receipt_share_product_then_stock_lock_order(
    db_session: Session,
) -> None:
    product_id, location_id = _seed_product(db_session)
    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    start = Barrier(2)
    state_lock = Lock()
    thread_roles: dict[int, str] = {}
    receipt_has_product_lock: set[int] = set()
    restock_product_locked = Event()
    legacy_receipt_stock_locked = Event()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            role = thread_roles.get(thread_id)

        if (
            role == "receipt"
            and normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "FOR UPDATE" in normalized
        ):
            with state_lock:
                receipt_has_product_lock.add(thread_id)
            return

        if (
            role == "restock"
            and normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "FOR UPDATE" in normalized
        ):
            restock_product_locked.set()
            # On the legacy opposite-order path, let the receipt acquire Stock
            # before the restock continues. On the fixed path the receipt blocks
            # on Product instead, so this short wait simply expires.
            legacy_receipt_stock_locked.wait(timeout=0.75)
            return

        if not (
            role == "receipt"
            and normalized.startswith("SELECT")
            and "FROM STOCK" in normalized
            and "FOR UPDATE" in normalized
        ):
            return

        with state_lock:
            already_locked_product = thread_id in receipt_has_product_lock
        if not already_locked_product:
            legacy_receipt_stock_locked.set()
            restock_product_locked.wait(timeout=5)

    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    def run_restock() -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            thread_roles[thread_id] = "restock"
        try:
            start.wait(timeout=10)
            try:
                result = products.restock_product(
                    product_id,
                    ProductRestockRequest(
                        location_id=location_id,
                        cantidad=5,
                        costo_unitario=Decimal("200.00"),
                    ),
                    session,
                    _user(),
                )
                return 200, str(result.costo)
            except Exception as exc:  # noqa: BLE001 - regression captures DB deadlocks
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            with state_lock:
                thread_roles.pop(thread_id, None)
            session.close()

    def run_receipt() -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            thread_roles[thread_id] = "receipt"
        try:
            start.wait(timeout=10)
            try:
                result = multistore_control.create_purchase_receipt(
                    PurchaseReceiptCreate(
                        location_id=location_id,
                        invoice_number=f"LOCK-{uuid4().hex}",
                        items=[
                            PurchaseReceiptItemCreate(
                                product_id=product_id,
                                quantity=2,
                                unit_cost=Decimal("300.00"),
                            )
                        ],
                    ),
                    session,
                    _user(),
                )
                return 200, str(result.total_cost)
            except Exception as exc:  # noqa: BLE001 - regression captures DB deadlocks
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            with state_lock:
                thread_roles.pop(thread_id, None)
                receipt_has_product_lock.discard(thread_id)
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_restock), pool.submit(run_receipt)]
            results = [future.result(timeout=20) for future in futures]
    finally:
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert sorted(status for status, _ in results) == [200, 200]

    db_session.expire_all()
    stock = (
        db_session.query(Stock)
        .filter(
            Stock.product_id == product_id,
            Stock.location_id == location_id,
        )
        .one()
    )
    assert stock.cantidad_disponible == 17
    assert db_session.query(PurchaseReceipt).count() == 1
    assert (
        db_session.query(StockHistory)
        .filter(
            StockHistory.product_id == product_id,
            StockHistory.location_id == location_id,
        )
        .count()
        == 2
    )


def test_purchase_receipts_lock_products_in_deterministic_order(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    location = Location(
        nombre=f"Tienda Reverse Receipt {suffix}",
        tipo="tienda",
        activo=True,
    )
    db_session.add(location)
    db_session.flush()
    first_product_id, location_id = _seed_product(
        db_session,
        location=location,
        initial_stock=5,
    )
    second_product_id, _ = _seed_product(
        db_session,
        location=location,
        initial_stock=5,
    )

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    start = Barrier(2)
    legacy_first_stock_barrier = Barrier(2)
    state_lock = Lock()
    worker_threads: set[int] = set()
    product_lock_seen: set[int] = set()
    first_stock_seen: set[int] = set()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            if thread_id not in worker_threads:
                return

        if (
            normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "FOR UPDATE" in normalized
        ):
            with state_lock:
                product_lock_seen.add(thread_id)
            return

        if not (
            normalized.startswith("SELECT")
            and "FROM STOCK" in normalized
            and "FOR UPDATE" in normalized
        ):
            return

        with state_lock:
            legacy_path = thread_id not in product_lock_seen
            first_for_thread = thread_id not in first_stock_seen
            if first_for_thread:
                first_stock_seen.add(thread_id)
        if legacy_path and first_for_thread:
            # Legacy purchase receipts lock the first Stock row according to
            # payload order. Two reversed payloads therefore hold opposite rows
            # before requesting the other one and deterministically deadlock.
            legacy_first_stock_barrier.wait(timeout=10)

    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    def run_receipt(order: tuple[int, int]) -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            worker_threads.add(thread_id)
        try:
            start.wait(timeout=10)
            try:
                result = multistore_control.create_purchase_receipt(
                    PurchaseReceiptCreate(
                        location_id=location_id,
                        invoice_number=f"REVERSE-{uuid4().hex}",
                        items=[
                            PurchaseReceiptItemCreate(
                                product_id=order[0],
                                quantity=1,
                                unit_cost=Decimal("110.00"),
                            ),
                            PurchaseReceiptItemCreate(
                                product_id=order[1],
                                quantity=1,
                                unit_cost=Decimal("120.00"),
                            ),
                        ],
                    ),
                    session,
                    _user(),
                )
                return 200, str(result.total_cost)
            except Exception as exc:  # noqa: BLE001 - regression captures DB deadlocks
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            with state_lock:
                worker_threads.discard(thread_id)
                product_lock_seen.discard(thread_id)
                first_stock_seen.discard(thread_id)
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(run_receipt, (first_product_id, second_product_id)),
                pool.submit(run_receipt, (second_product_id, first_product_id)),
            ]
            results = [future.result(timeout=20) for future in futures]
    finally:
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert sorted(status for status, _ in results) == [200, 200]

    db_session.expire_all()
    stocks = {
        row.product_id: row.cantidad_disponible
        for row in db_session.query(Stock)
        .filter(
            Stock.location_id == location_id,
            Stock.product_id.in_([first_product_id, second_product_id]),
        )
        .all()
    }
    assert stocks == {
        first_product_id: 7,
        second_product_id: 7,
    }
    assert db_session.query(PurchaseReceipt).count() == 2
