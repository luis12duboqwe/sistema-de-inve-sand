from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Event, Lock, get_ident
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, Stock, StockHistory
from app.models.control import PhysicalInventoryCount, PhysicalInventoryCountItem
from app.routers import multistore_control, products
from app.schemas import ProductRestockRequest
from app.schemas.control import InventoryCountApproveRequest


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="restock-count-lock-compat",
        is_superuser=True,
        role=None,
    )


def _normalized(statement: str) -> str:
    return " ".join(statement.upper().split())


def test_restock_no_key_update_is_compatible_with_inventory_count_history_fk(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    location = Location(
        nombre=f"Tienda Count Lock {suffix}",
        tipo="tienda",
        activo=True,
    )
    product = Product(
        sku=f"COUNT-LOCK-{suffix}",
        nombre=f"Producto Count Lock {suffix}",
        categoria="accesorio",
        marca="Marca QA",
        modelo=f"Modelo-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("100.00"),
        moneda="Lps",
        garantia_meses=0,
        activo=True,
        is_serialized=False,
    )
    db_session.add_all([location, product])
    db_session.flush()
    product_id = int(product.id)
    location_id = int(location.id)

    db_session.add(
        Stock(
            product_id=product_id,
            location_id=location_id,
            cantidad_disponible=10,
            cantidad_reservada=0,
            cantidad_defectuosa=0,
        )
    )
    count = PhysicalInventoryCount(
        location_id=location_id,
        status="draft",
        counted_by="qa",
        notes="concurrency regression",
    )
    db_session.add(count)
    db_session.flush()
    count_id = int(count.id)
    db_session.add(
        PhysicalInventoryCountItem(
            count_id=count_id,
            product_id=product_id,
            expected_quantity=10,
            counted_quantity=20,
            difference=10,
            imeis_json=None,
            notes="counted",
        )
    )
    db_session.commit()

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    start = Barrier(2)
    state_lock = Lock()
    thread_roles: dict[int, str] = {}
    restock_product_locked = Event()
    count_stock_locked = Event()
    restock_stock_lock_attempted = Event()
    restock_product_lock_sql: list[str] = []
    restock_stock_lock_sql: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            role = thread_roles.get(thread_id)

        if (
            role == "restock"
            and normalized.startswith("SELECT")
            and "FROM STOCK" in normalized
            and "FOR UPDATE" in normalized
        ):
            with state_lock:
                restock_stock_lock_sql.append(normalized)
            restock_stock_lock_attempted.set()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            role = thread_roles.get(thread_id)

        if (
            role == "restock"
            and normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and ("FOR UPDATE" in normalized or "FOR NO KEY UPDATE" in normalized)
        ):
            with state_lock:
                restock_product_lock_sql.append(normalized)
            restock_product_locked.set()
            count_stock_locked.wait(timeout=5)
            return

        if (
            role == "count"
            and normalized.startswith("SELECT")
            and "FROM STOCK" in normalized
            and "FOR UPDATE" in normalized
        ):
            count_stock_locked.set()
            restock_product_locked.wait(timeout=5)
            restock_stock_lock_attempted.wait(timeout=5)

    event.listen(bind, "before_cursor_execute", before_cursor_execute)
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

    def run_count_approval() -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            thread_roles[thread_id] = "count"
        try:
            start.wait(timeout=10)
            try:
                result = multistore_control.approve_inventory_count(
                    count_id,
                    InventoryCountApproveRequest(notes="approved concurrently"),
                    session,
                    _user(),
                )
                return 200, result.status
            except Exception as exc:  # noqa: BLE001 - regression captures DB deadlocks
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            with state_lock:
                thread_roles.pop(thread_id, None)
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_restock), pool.submit(run_count_approval)]
            results = [future.result(timeout=20) for future in futures]
    finally:
        event.remove(bind, "before_cursor_execute", before_cursor_execute)
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert sorted(status for status, _ in results) == [200, 200]
    assert restock_product_lock_sql
    assert all("FOR NO KEY UPDATE" in sql for sql in restock_product_lock_sql)
    assert restock_stock_lock_sql
    assert all("FOR UPDATE" in sql for sql in restock_stock_lock_sql)

    db_session.expire_all()
    stock = (
        db_session.query(Stock)
        .filter(
            Stock.product_id == product_id,
            Stock.location_id == location_id,
        )
        .one()
    )
    persisted_product = db_session.get(Product, product_id)
    persisted_count = db_session.get(PhysicalInventoryCount, count_id)
    assert persisted_product is not None
    assert persisted_count is not None
    assert persisted_count.status == "approved"
    assert stock.cantidad_disponible == 25
    assert Decimal(persisted_product.costo) == Decimal("120.00")
    assert (
        db_session.query(StockHistory)
        .filter(
            StockHistory.product_id == product_id,
            StockHistory.location_id == location_id,
            StockHistory.tipo_cambio == "CONTEO_FISICO",
        )
        .count()
        == 1
    )
    assert (
        db_session.query(StockHistory)
        .filter(
            StockHistory.product_id == product_id,
            StockHistory.location_id == location_id,
            StockHistory.tipo_cambio == "compra",
        )
        .count()
        == 1
    )
