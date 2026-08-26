from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import app.database as database
from app.location_identity import location_name_hash, location_name_key
from app.models import Location
from app.routers import locations
from app.schemas import LocationCreate, LocationUpdate
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
                created = locations.create_location(
                    LocationCreate(nombre=name, tipo="tienda"),
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
    location_ids: tuple[int, int],
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
        location_id, name = args
        session = SessionLocal()
        try:
            try:
                updated = locations.update_location(
                    location_id,
                    LocationUpdate(nombre=name),
                    session,
                    SimpleNamespace(),
                )
                return (200, updated.nombre)
            except HTTPException as exc:
                return (exc.status_code, exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(update, zip(location_ids, names)))


def _create_legacy_sqlite_schema(engine, location_rows: list[tuple[int, str]]) -> None:
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
                "CREATE TABLE locations ("
                "id INTEGER PRIMARY KEY, nombre VARCHAR NOT NULL, "
                "tipo VARCHAR NOT NULL, activo BOOLEAN NOT NULL DEFAULT 1)"
            )
        )
        for location_id, name in location_rows:
            conn.execute(
                text(
                    "INSERT INTO locations (id, nombre, tipo) "
                    "VALUES (:id, :name, 'tienda')"
                ),
                {"id": location_id, "name": name},
            )


def _normalized_location_count(db_session: Session, name: str) -> int:
    return (
        db_session.query(Location)
        .filter(Location.nombre_key_hash == location_name_hash(name))
        .count()
    )


def test_location_precheck_uses_unicode_aware_trimmed_identity(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    original_name = f"Águila Tienda {suffix}"
    db_session.add(Location(nombre=f"  {original_name}  ", tipo="tienda", activo=True))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        locations.create_location(
            LocationCreate(nombre=f"ÁGUILA TIENDA {suffix}", tipo="tienda"),
            db_session,
            SimpleNamespace(),
        )

    assert exc_info.value.status_code == 400
    assert "ya existe" in str(exc_info.value.detail)


def test_concurrent_location_create_leaves_one_normalized_name(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    canonical = f"Águila-Location-Race-{suffix}"

    results = _run_concurrent_create(
        db_session,
        (canonical, f"  ÁGUILA-LOCATION-RACE-{suffix}  "),
    )

    assert sorted(status for status, _ in results) == [201, 400]
    assert any(
        "ya existe" in str(detail)
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert _normalized_location_count(db_session, canonical) == 1


def test_concurrent_location_updates_cannot_converge_on_same_name(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    first = Location(nombre=f"Origen-A-{suffix}", tipo="tienda", activo=True)
    second = Location(nombre=f"Origen-B-{suffix}", tipo="bodega", activo=True)
    db_session.add_all([first, second])
    db_session.commit()
    first_id = int(first.id)
    second_id = int(second.id)

    canonical = f"Águila-Location-Update-{suffix}"
    results = _run_concurrent_update(
        db_session,
        (first_id, second_id),
        (canonical, f"  ÁGUILA-LOCATION-UPDATE-{suffix}  "),
    )

    assert sorted(status for status, _ in results) == [200, 400]
    assert any(
        "ya existe" in str(detail)
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert _normalized_location_count(db_session, canonical) == 1
    assert (
        db_session.query(Location)
        .filter(Location.id.in_([first_id, second_id]))
        .count()
        == 2
    )


def test_unrelated_location_integrity_conflict_is_not_mislabeled_as_duplicate(
    db_session: Session,
) -> None:
    error = locations._location_integrity_error(
        db_session,
        f"missing-{uuid4().hex}",
    )

    assert error.status_code == 409
    assert "integridad" in str(error.detail).lower()


def test_location_name_migration_fails_closed_on_unicode_historical_duplicates(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "location-duplicates.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(
        engine,
        [(1, "ÁGUILA CENTRO"), (2, "  águila centro  ")],
    )
    monkeypatch.setattr(database, "engine", engine)

    try:
        with pytest.raises(RuntimeError, match="Ubicaciones duplicadas después de normalizar"):
            run_auto_migrations()

        with engine.connect() as conn:
            names = conn.execute(text("SELECT nombre FROM locations ORDER BY id")).scalars().all()
            applied = {
                str(row[0])
                for row in conn.execute(text("SELECT id FROM schema_migrations"))
            }
        assert names == ["ÁGUILA CENTRO", "  águila centro  "]
        assert "20260826_01_location_name_uniqueness" not in applied
    finally:
        engine.dispose()


def test_location_name_migration_preserves_data_and_enforces_hash_unique_index(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "location-unique.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(
        engine,
        [(1, "  Águila Centro  "), (2, "Bodega Norte")],
    )
    monkeypatch.setattr(database, "engine", engine)

    try:
        assert run_auto_migrations() is True
        assert run_auto_migrations() is True

        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT nombre, nombre_normalized, nombre_key_hash "
                    "FROM locations ORDER BY id"
                )
            ).mappings().all()
            indexes = conn.execute(text("PRAGMA index_list('locations')")).fetchall()

        assert [row["nombre"] for row in rows] == ["  Águila Centro  ", "Bodega Norte"]
        assert rows[0]["nombre_normalized"] == location_name_key("ÁGUILA CENTRO")
        assert rows[0]["nombre_key_hash"] == location_name_hash("águila centro")
        assert any(
            str(row[1]) == "ix_locations_nombre_key_hash" and bool(row[2])
            for row in indexes
        )

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO locations "
                        "(id, nombre, tipo, nombre_normalized, nombre_key_hash) "
                        "VALUES (3, :name, 'tienda', :normalized, :digest)"
                    ),
                    {
                        "name": "ÁGUILA CENTRO",
                        "normalized": location_name_key("ÁGUILA CENTRO"),
                        "digest": location_name_hash("ÁGUILA CENTRO"),
                    },
                )
    finally:
        engine.dispose()
