from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import app.database as database
from app.models import Supplier
from app.routers import suppliers
from app.schemas import SupplierCreate, SupplierUpdate
from app.utils.auto_migrations import run_auto_migrations


def _run_concurrent_create(db_session: Session, names: tuple[str, str]):
    bind = db_session.get_bind()
    barrier = Barrier(2)

    class BarrierSession(Session):
        def commit(self):
            barrier.wait(timeout=10)
            return super().commit()

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=bind,
        class_=BarrierSession,
    )

    def create(name: str):
        session = SessionLocal()
        try:
            try:
                created = suppliers.create_supplier(
                    SupplierCreate(nombre=name),
                    session,
                    SimpleNamespace(),
                )
                return (201, created.nombre)
            except HTTPException as exc:
                return (exc.status_code, exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(create, names))


def _run_concurrent_update(
    db_session: Session,
    supplier_ids: tuple[int, int],
    names: tuple[str, str],
):
    bind = db_session.get_bind()
    barrier = Barrier(2)

    class BarrierSession(Session):
        def commit(self):
            barrier.wait(timeout=10)
            return super().commit()

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=bind,
        class_=BarrierSession,
    )

    def update(args: tuple[int, str]):
        supplier_id, name = args
        session = SessionLocal()
        try:
            try:
                updated = suppliers.update_supplier(
                    supplier_id,
                    SupplierUpdate(nombre=name),
                    session,
                    SimpleNamespace(),
                )
                return (200, updated.nombre)
            except HTTPException as exc:
                return (exc.status_code, exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(update, zip(supplier_ids, names)))


def _create_legacy_sqlite_schema(engine, supplier_rows: list[tuple[int, str]]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE orders (id INTEGER PRIMARY KEY, estado VARCHAR(50), total NUMERIC)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE stock_transfers (id INTEGER PRIMARY KEY, cantidad INTEGER, estado VARCHAR(50))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE suppliers ("
                "id INTEGER PRIMARY KEY, nombre VARCHAR NOT NULL, activo BOOLEAN NOT NULL DEFAULT 1)"
            )
        )
        for supplier_id, name in supplier_rows:
            conn.execute(
                text("INSERT INTO suppliers (id, nombre) VALUES (:id, :name)"),
                {"id": supplier_id, "name": name},
            )


def test_supplier_precheck_uses_same_trimmed_case_insensitive_identity(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    original_name = f"Proveedor {suffix}"
    db_session.add(Supplier(nombre=f"  {original_name}  ", activo=True))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        suppliers.create_supplier(
            SupplierCreate(nombre=original_name.upper()),
            db_session,
            SimpleNamespace(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in str(exc_info.value.detail)


def test_concurrent_supplier_create_leaves_one_normalized_name(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    canonical = f"proveedor-race-{suffix}"

    results = _run_concurrent_create(
        db_session,
        (f"Proveedor-Race-{suffix}", f"  PROVEEDOR-RACE-{suffix}  "),
    )

    assert sorted(status for status, _ in results) == [201, 400]
    assert any(
        "ya existe" in str(detail)
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert (
        db_session.query(Supplier)
        .filter(func.lower(func.trim(Supplier.nombre)) == canonical)
        .count()
        == 1
    )


def test_concurrent_supplier_updates_cannot_converge_on_same_name(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    first = Supplier(nombre=f"Origen-A-{suffix}", activo=True)
    second = Supplier(nombre=f"Origen-B-{suffix}", activo=True)
    db_session.add_all([first, second])
    db_session.commit()
    first_id = int(first.id)
    second_id = int(second.id)

    canonical = f"proveedor-update-race-{suffix}"
    results = _run_concurrent_update(
        db_session,
        (first_id, second_id),
        (f"Proveedor-Update-Race-{suffix}", f"  PROVEEDOR-UPDATE-RACE-{suffix}  "),
    )

    assert sorted(status for status, _ in results) == [200, 400]
    assert any(
        "ya existe" in str(detail)
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert (
        db_session.query(Supplier)
        .filter(func.lower(func.trim(Supplier.nombre)) == canonical)
        .count()
        == 1
    )
    assert db_session.query(Supplier).filter(Supplier.id.in_([first_id, second_id])).count() == 2


def test_unrelated_supplier_integrity_conflict_is_not_mislabeled_as_duplicate(
    db_session: Session,
) -> None:
    error = suppliers._supplier_integrity_error(
        db_session,
        f"missing-{uuid4().hex}",
    )

    assert error.status_code == 409
    assert "integridad" in str(error.detail).lower()


def test_supplier_name_migration_fails_closed_on_historical_duplicates(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "supplier-duplicates.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(
        engine,
        [(1, "ACME"), (2, "  acme  ")],
    )
    monkeypatch.setattr(database, "engine", engine)

    try:
        with pytest.raises(RuntimeError, match="Proveedores duplicados después de normalizar"):
            run_auto_migrations()

        with engine.connect() as conn:
            names = conn.execute(text("SELECT nombre FROM suppliers ORDER BY id")).scalars().all()
            applied = {
                str(row[0])
                for row in conn.execute(text("SELECT id FROM schema_migrations"))
            }
        assert names == ["ACME", "  acme  "]
        assert "20260825_01_supplier_name_uniqueness" not in applied
    finally:
        engine.dispose()


def test_supplier_name_migration_preserves_data_and_enforces_normalized_unique_index(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "supplier-unique.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(
        engine,
        [(1, "  Acme Corp  "), (2, "Beta")],
    )
    monkeypatch.setattr(database, "engine", engine)

    try:
        assert run_auto_migrations() is True
        assert run_auto_migrations() is True

        with engine.connect() as conn:
            names = conn.execute(text("SELECT nombre FROM suppliers ORDER BY id")).scalars().all()
            indexes = conn.execute(text("PRAGMA index_list('suppliers')")).fetchall()
        assert names == ["  Acme Corp  ", "Beta"]
        assert any(
            str(row[1]) == "ix_suppliers_nombre_normalized" and bool(row[2])
            for row in indexes
        )

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO suppliers (id, nombre) VALUES (3, 'acme corp')")
                )
    finally:
        engine.dispose()
