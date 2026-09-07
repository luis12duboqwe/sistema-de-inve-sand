from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, Lock, get_ident
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, Stock, StockTransfer
from app.routers import products
from app.routers.stock_transfer_integrity import confirm_transfer_integrity
from app.schemas import ProductRestockRequest, StockTransferConfirm


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="restock-transfer-lock-compat",
        is_superuser=True,
        is_active=True,
        role=None,
    )


def _normalized(statement: str) -> str:
    return " ".join(statement.upper().split())


def test_restock_and_transfer_confirmation_share_ordered_stock_lock_protocol(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    product = Product(
        sku=f"TRANSFER-RESTOCK-{suffix}",
        nombre=f"Producto Transfer Restock {suffix}",
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
    # Destination is inserted first so destination_id < source_id. This is the
    # inverse ordering that deadlocked when confirmation locked source first.
    destination = Location(
        nombre=f"Destino Transfer Restock {suffix}",
        tipo="tienda",
        activo=True,
    )
    source = Location(
        nombre=f"Origen Transfer Restock {suffix}",
        tipo="tienda",
        activo=True,
    )
    db_session.add_all([product, destination, source])
    db_session.flush()
    product_id = int(product.id)
    destination_id = int(destination.id)
    source_id = int(source.id)
    assert destination_id < source_id

    source_stock = Stock(
        product_id=product_id,
        location_id=source_id,
        cantidad_disponible=10,
        cantidad_reservada=3,
        cantidad_defectuosa=0,
    )
    destination_stock = Stock(
        product_id=product_id,
        location_id=destination_id,
        cantidad_disponible=5,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    transfer = StockTransfer(
        product_id=product_id,
        from_location_id=source_id,
        to_location_id=destination_id,
        cantidad=3,
        estado="pendiente",
        created_by="restock-transfer-lock-compat",
    )
    db_session.add_all([source_stock, destination_stock, transfer])
    db_session.commit()
    transfer_id = int(transfer.id)

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    start = Barrier(2)
    state_lock = Lock()
    thread_roles: dict[int, str] = {}
    confirmation_product_locks: list[str] = []
    confirmation_stock_locks: list[tuple[str, str]] = []

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        normalized = _normalized(statement)
        thread_id = get_ident()
        with state_lock:
            role = thread_roles.get(thread_id)
        if role != "confirm" or not normalized.startswith("SELECT"):
            return

        if "FROM PRODUCTS" in normalized and "FOR NO KEY UPDATE" in normalized:
            with state_lock:
                confirmation_product_locks.append(normalized)
            return

        if "FROM STOCK" in normalized and "FOR UPDATE" in normalized:
            with state_lock:
                confirmation_stock_locks.append((normalized, repr(parameters)))

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
                        location_id=destination_id,
                        cantidad=4,
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

    def run_confirmation() -> tuple[int, str]:
        session = SessionLocal()
        thread_id = get_ident()
        with state_lock:
            thread_roles[thread_id] = "confirm"
        try:
            start.wait(timeout=10)
            try:
                result = confirm_transfer_integrity(
                    transfer_id,
                    StockTransferConfirm(received_quantity=3),
                    db=session,
                    current_user=_user(),
                )
                return 200, str(result.estado)
            except Exception as exc:  # noqa: BLE001 - regression captures DB deadlocks
                session.rollback()
                return int(getattr(exc, "status_code", 500)), repr(exc)
        finally:
            with state_lock:
                thread_roles.pop(thread_id, None)
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_restock), pool.submit(run_confirmation)]
            results = [future.result(timeout=20) for future in futures]
    finally:
        event.remove(bind, "after_cursor_execute", after_cursor_execute)

    assert sorted(status for status, _ in results) == [200, 200]
    assert confirmation_product_locks
    assert confirmation_stock_locks

    first_stock_lock_sql, first_stock_lock_parameters = confirmation_stock_locks[0]
    assert "ORDER BY" in first_stock_lock_sql
    assert "STOCK.LOCATION_ID ASC" in first_stock_lock_sql
    assert "STOCK.ID ASC" in first_stock_lock_sql
    assert " IN " in first_stock_lock_sql
    assert str(source_id) in first_stock_lock_parameters
    assert str(destination_id) in first_stock_lock_parameters

    db_session.expire_all()
    persisted_source = (
        db_session.query(Stock)
        .filter(Stock.product_id == product_id, Stock.location_id == source_id)
        .one()
    )
    persisted_destination = (
        db_session.query(Stock)
        .filter(Stock.product_id == product_id, Stock.location_id == destination_id)
        .one()
    )
    persisted_transfer = db_session.get(StockTransfer, transfer_id)
    persisted_product = db_session.get(Product, product_id)

    assert persisted_transfer is not None
    assert persisted_product is not None
    assert persisted_transfer.estado == "confirmada"
    assert persisted_source.cantidad_disponible == 7
    assert persisted_source.cantidad_reservada == 0
    assert persisted_destination.cantidad_disponible == 12
    assert Decimal(persisted_product.costo) == Decimal("60.53")
