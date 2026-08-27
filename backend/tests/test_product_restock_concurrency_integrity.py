from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Lock, get_ident
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, Stock, StockHistory
from app.routers import products
from app.schemas import ProductRestockRequest


def _seed_product(
    db_session: Session,
    *,
    initial_stock: int | None,
    initial_cost: Decimal,
) -> tuple[int, int]:
    suffix = uuid4().hex
    location = Location(
        nombre=f"Tienda Restock {suffix}",
        tipo="tienda",
        activo=True,
    )
    product = Product(
        sku=f"RESTOCK-{suffix}",
        nombre=f"Producto Restock {suffix}",
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
    db_session.add_all([location, product])
    db_session.flush()

    if initial_stock is not None:
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


def _run_concurrent_restocks(
    db_session: Session,
    *,
    product_id: int,
    payloads: tuple[ProductRestockRequest, ProductRestockRequest],
) -> list[tuple[int, str]]:
    """Run two real PostgreSQL restocks and deterministically expose the old race.

    If the production product lookup does not use ``FOR UPDATE``, both workers are
    paused immediately after their first Stock SELECT has executed. That guarantees
    both legacy transactions observed the same pre-restock state before either can
    mutate it. Once the production Product SELECT is locking, the second transaction
    blocks there instead, so no artificial Stock barrier is applied and the requests
    serialize naturally on PostgreSQL.
    """

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    start_barrier = Barrier(2)
    legacy_stock_barrier = Barrier(2)
    state_lock = Lock()
    product_lock_by_thread: dict[int, bool] = {}
    stock_barrier_used: set[int] = set()

    def _normalized(statement: str) -> str:
        return " ".join(statement.upper().split())

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        if (
            normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "PRODUCTS.ID" in normalized
        ):
            thread_id = get_ident()
            with state_lock:
                product_lock_by_thread.setdefault(
                    thread_id,
                    "FOR UPDATE" in normalized,
                )

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        if not (normalized.startswith("SELECT") and "FROM STOCK" in normalized):
            return

        thread_id = get_ident()
        with state_lock:
            has_product_lock = product_lock_by_thread.get(thread_id)
            should_wait = has_product_lock is False and thread_id not in stock_barrier_used
            if should_wait:
                stock_barrier_used.add(thread_id)

        if should_wait:
            legacy_stock_barrier.wait(timeout=10)

    event.listen(bind, "before_cursor_execute", before_cursor_execute)
    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    user = SimpleNamespace(
        id=1,
        username="restock-concurrency",
        is_superuser=True,
        role=None,
    )

    def worker(payload: ProductRestockRequest) -> tuple[int, str]:
        session = SessionLocal()
        try:
            start_barrier.wait(timeout=10)
            try:
                result = products.restock_product(
                    product_id,
                    payload,
                    session,
                    user,
                )
                return 200, str(result.costo)
            except Exception as exc:  # noqa: BLE001 - regression captures old DB race
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, payload) for payload in payloads]
            return [future.result(timeout=20) for future in futures]
    finally:
        event.remove(bind, "before_cursor_execute", before_cursor_execute)
        event.remove(bind, "after_cursor_execute", after_cursor_execute)


def test_concurrent_restocks_preserve_stock_and_weighted_cost(
    db_session: Session,
) -> None:
    product_id, location_id = _seed_product(
        db_session,
        initial_stock=10,
        initial_cost=Decimal("100.00"),
    )

    results = _run_concurrent_restocks(
        db_session,
        product_id=product_id,
        payloads=(
            ProductRestockRequest(
                location_id=location_id,
                cantidad=5,
                costo_unitario=Decimal("200.00"),
            ),
            ProductRestockRequest(
                location_id=location_id,
                cantidad=5,
                costo_unitario=Decimal("300.00"),
            ),
        ),
    )

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
    product = db_session.get(Product, product_id)
    assert product is not None
    assert stock.cantidad_disponible == 20
    assert Decimal(product.costo) == Decimal("175.00")
    assert (
        db_session.query(StockHistory)
        .filter(
            StockHistory.product_id == product_id,
            StockHistory.location_id == location_id,
            StockHistory.tipo_cambio == "compra",
        )
        .count()
        == 2
    )


def test_concurrent_first_restocks_create_one_stock_row_and_keep_both_receipts(
    db_session: Session,
) -> None:
    product_id, location_id = _seed_product(
        db_session,
        initial_stock=None,
        initial_cost=Decimal("0.00"),
    )

    results = _run_concurrent_restocks(
        db_session,
        product_id=product_id,
        payloads=(
            ProductRestockRequest(
                location_id=location_id,
                cantidad=2,
                costo_unitario=Decimal("100.00"),
            ),
            ProductRestockRequest(
                location_id=location_id,
                cantidad=3,
                costo_unitario=Decimal("200.00"),
            ),
        ),
    )

    assert sorted(status for status, _ in results) == [200, 200]

    db_session.expire_all()
    stocks = (
        db_session.query(Stock)
        .filter(
            Stock.product_id == product_id,
            Stock.location_id == location_id,
        )
        .all()
    )
    product = db_session.get(Product, product_id)
    assert product is not None
    assert len(stocks) == 1
    assert stocks[0].cantidad_disponible == 5
    assert Decimal(product.costo) == Decimal("160.00")
    assert (
        db_session.query(StockHistory)
        .filter(
            StockHistory.product_id == product_id,
            StockHistory.location_id == location_id,
            StockHistory.tipo_cambio == "compra",
        )
        .count()
        == 2
    )
