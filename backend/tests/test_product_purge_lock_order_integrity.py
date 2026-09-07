from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event, Lock, get_ident
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, Stock
from app.routers import products, super_admin
from app.schemas import ProductRestockRequest


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


def test_product_purge_locks_product_before_stock_against_restock(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    location = Location(
        nombre=f"Tienda Purge Lock {suffix}",
        tipo="tienda",
        activo=True,
    )
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
    db_session.commit()

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    state_lock = Lock()
    thread_roles: dict[int, str] = {}
    restock_product_locked = Event()
    purge_product_lock_attempted = Event()
    purge_stock_delete_attempted = Event()
    purge_product_lock_sql: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            role = thread_roles.get(thread_id)
        if role != "purge":
            return

        if (
            normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "FOR UPDATE" in normalized
        ):
            with state_lock:
                purge_product_lock_sql.append(normalized)
            purge_product_lock_attempted.set()
            return

        if normalized.startswith("DELETE FROM STOCK "):
            purge_stock_delete_attempted.set()

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            role = thread_roles.get(thread_id)
        if not (
            role == "restock"
            and normalized.startswith("SELECT")
            and "FROM PRODUCTS" in normalized
            and "FOR NO KEY UPDATE" in normalized
        ):
            return

        restock_product_locked.set()
        deadline = monotonic() + 5
        while monotonic() < deadline:
            if purge_product_lock_attempted.is_set() or purge_stock_delete_attempted.is_set():
                return
            sleep(0.01)
        raise AssertionError("Purge never attempted Product or Stock while restock held Product")

    event.listen(bind, "before_cursor_execute", before_cursor_execute)
    event.listen(bind, "after_cursor_execute", after_cursor_execute)

    def run_restock() -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            thread_roles[thread_id] = "restock"
        try:
            try:
                result = products.restock_product(
                    product_id,
                    ProductRestockRequest(
                        location_id=location_id,
                        cantidad=2,
                        costo_unitario=Decimal("100.00"),
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

    def run_purge() -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            thread_roles[thread_id] = "purge"
        try:
            if not restock_product_locked.wait(timeout=10):
                return 500, "restock never acquired Product lock"
            try:
                result = super_admin.purge_product_for_admin(
                    product_id,
                    super_admin.ProductPurgeRequest(
                        reason="Prueba concurrente de orden Product antes de Stock"
                    ),
                    session,
                    _user(),
                )
                return 200, str(result["ok"])
            except Exception as exc:  # noqa: BLE001 - regression captures DB deadlocks
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            with state_lock:
                thread_roles.pop(thread_id, None)
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            restock_future = pool.submit(run_restock)
            purge_future = pool.submit(run_purge)
            results = [
                restock_future.result(timeout=20),
                purge_future.result(timeout=20),
            ]
    finally:
        event.remove(bind, "before_cursor_execute", before_cursor_execute)
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert sorted(status for status, _ in results) == [200, 200]
    assert purge_product_lock_attempted.is_set()
    assert purge_product_lock_sql
    assert purge_stock_delete_attempted.is_set()

    db_session.expire_all()
    assert db_session.query(Product).filter(Product.id == product_id).count() == 0
    assert db_session.query(Stock).filter(Stock.product_id == product_id).count() == 0
