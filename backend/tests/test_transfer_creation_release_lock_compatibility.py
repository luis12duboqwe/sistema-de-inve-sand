from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event, Lock, get_ident
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Location, Product, Stock, StockHistory, StockTransfer
from app.routers.stock_transfer_integrity import reject_transfer_integrity
from app.routers.stock_transfers import create_transfer
from app.schemas import StockTransferCreate, StockTransferReject


def test_transfer_creation_does_not_deadlock_with_reservation_release(db_session: Session):
    suffix = uuid4().hex
    product = Product(
        sku=f"TRANSFER-RELEASE-{suffix}", nombre=f"Transfer Release {suffix}",
        categoria="accesorio", marca="QA", modelo=suffix[:8], condicion="nuevo",
        precio=Decimal("100"), costo=Decimal("50"), moneda="Lps",
        garantia_meses=0, activo=True, is_serialized=False,
    )
    source = Location(nombre=f"Source {suffix}", tipo="tienda", activo=True)
    destination = Location(nombre=f"Destination {suffix}", tipo="tienda", activo=True)
    db_session.add_all([product, source, destination])
    db_session.flush()
    product_id, source_id, destination_id = product.id, source.id, destination.id
    db_session.add(Stock(product_id=product_id, location_id=source_id,
                         cantidad_disponible=10, cantidad_reservada=2,
                         cantidad_defectuosa=0))
    transfer = StockTransfer(product_id=product_id, from_location_id=source_id,
                             to_location_id=destination_id, cantidad=2,
                             estado="pendiente", created_by="qa")
    db_session.add(transfer)
    db_session.commit()
    transfer_id = transfer.id

    bind = db_session.get_bind()
    SessionLocal = sessionmaker(bind=bind, autoflush=False)
    release_has_stock = Event()
    create_attempted_product = Event()
    state_lock = Lock()
    roles = {}
    product_sql = []

    def before_execute(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(statement.upper().split())
        with state_lock:
            role = roles.get(get_ident())
        if role == "create" and "FROM PRODUCTS" in sql and "FOR " in sql:
            product_sql.append(sql)
            create_attempted_product.set()

    def after_execute(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(statement.upper().split())
        with state_lock:
            role = roles.get(get_ident())
        if role == "release" and "FROM STOCK " in sql and "FOR UPDATE" in sql:
            release_has_stock.set()
            assert create_attempted_product.wait(timeout=10)

    event.listen(bind, "before_cursor_execute", before_execute)
    event.listen(bind, "after_cursor_execute", after_execute)
    user = SimpleNamespace(id=1, username="qa", is_superuser=True, is_active=True, role=None)

    def run(role):
        session = SessionLocal()
        with state_lock:
            roles[get_ident()] = role
        try:
            if role == "create":
                assert release_has_stock.wait(timeout=10)
                create_transfer(
                    StockTransferCreate(product_id=product_id, from_location_id=source_id,
                                        to_location_id=destination_id, cantidad=3),
                    session, user,
                )
            else:
                reject_transfer_integrity(
                    transfer_id, StockTransferReject(rejection_reason="QA"),
                    session, user,
                )
            return 200
        except Exception as exc:
            session.rollback()
            return getattr(exc, "status_code", 500), repr(exc)
        finally:
            with state_lock:
                roles.pop(get_ident(), None)
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(run, "release")
            b = pool.submit(run, "create")
            results = [a.result(timeout=25), b.result(timeout=25)]
    finally:
        event.remove(bind, "before_cursor_execute", before_execute)
        event.remove(bind, "after_cursor_execute", after_execute)

    assert results == [200, 200]
    assert product_sql and all("FOR NO KEY UPDATE" in sql for sql in product_sql)
    db_session.expire_all()
    stock = db_session.query(Stock).filter_by(product_id=product_id, location_id=source_id).one()
    assert (stock.cantidad_disponible, stock.cantidad_reservada) == (10, 3)
    assert db_session.get(StockTransfer, transfer_id).estado == "rechazada"
    assert db_session.query(StockTransfer).filter_by(product_id=product_id, estado="pendiente").count() == 1
    assert db_session.query(StockHistory).filter_by(product_id=product_id, location_id=source_id).count() == 2
