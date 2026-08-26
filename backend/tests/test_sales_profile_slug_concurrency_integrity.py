from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

import app.database as database
from app.models import SalesProfile
from app.routers import channel_monitoring, sales_profiles
from app.sales_profile_identity import sales_profile_slug_hash, sales_profile_slug_key
from app.schemas import SalesProfileCreate, SalesProfileUpdate
from app.utils.auto_migrations import run_auto_migrations
from app.utils.order_queries import resolve_sales_profile_for_query
from app.utils.order_validators import resolve_sales_profile


def _profile(name: str, slug: str) -> SalesProfile:
    return SalesProfile(name=name, slug=slug, tipo="bot_ia", active=True)


def _run_concurrent_create(db_session: Session, slugs: tuple[str, str]):
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

    def create(slug: str):
        session = SessionLocal()
        try:
            try:
                created = sales_profiles.create_sales_profile(
                    SalesProfileCreate(
                        name=f"Perfil {uuid4().hex}",
                        slug=slug,
                        tipo="bot_ia",
                    ),
                    session,
                    SimpleNamespace(),
                )
                return (201, created["slug"])
            except HTTPException as exc:
                return (exc.status_code, exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(create, slugs))


def _run_concurrent_update(
    db_session: Session,
    profile_ids: tuple[int, int],
    slugs: tuple[str, str],
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
        profile_id, slug = args
        session = SessionLocal()
        try:
            try:
                updated = sales_profiles.update_sales_profile(
                    profile_id,
                    SalesProfileUpdate(slug=slug),
                    session,
                    SimpleNamespace(),
                )
                return (200, updated["slug"])
            except HTTPException as exc:
                return (exc.status_code, exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(update, zip(profile_ids, slugs)))


def _create_legacy_sqlite_schema(engine, rows: list[tuple[int, str]]) -> None:
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
                "CREATE TABLE sales_profiles ("
                "id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, slug VARCHAR UNIQUE NOT NULL, "
                "tipo VARCHAR NOT NULL, active BOOLEAN NOT NULL DEFAULT 1)"
            )
        )
        for profile_id, slug in rows:
            conn.execute(
                text(
                    "INSERT INTO sales_profiles (id, name, slug, tipo) "
                    "VALUES (:id, :name, :slug, 'bot_ia')"
                ),
                {
                    "id": profile_id,
                    "name": f"Perfil {profile_id}",
                    "slug": slug,
                },
            )


def _normalized_slug_count(db_session: Session, slug: str) -> int:
    return (
        db_session.query(SalesProfile)
        .filter(SalesProfile.slug_key_hash == sales_profile_slug_hash(slug))
        .count()
    )


def test_sales_profile_precheck_uses_unicode_aware_trimmed_slug_identity(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    original_slug = f"bót-{suffix}"
    db_session.add(_profile("Perfil original", f"  {original_slug}  "))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        sales_profiles.create_sales_profile(
            SalesProfileCreate(
                name="Perfil duplicado",
                slug=f"BÓT-{suffix}",
                tipo="bot_ia",
            ),
            db_session,
            SimpleNamespace(),
        )

    assert exc_info.value.status_code == 400
    assert "ignora mayúsculas/minúsculas" in str(exc_info.value.detail)


def test_sales_profile_lookup_by_slug_uses_same_case_insensitive_identity(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    profile = _profile("Perfil lookup", f"Bót-Lookup-{suffix}")
    db_session.add(profile)
    db_session.commit()

    result = sales_profiles.get_sales_profile_by_slug(
        f"bÓT-LOOKUP-{suffix}",
        db=db_session,
    )

    assert result["id"] == profile.id
    assert result["slug"] == f"Bót-Lookup-{suffix}"


def test_sales_profile_slug_http_route_precedes_dynamic_id_route(
    client: TestClient,
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    slug = f"bot-route-{suffix}"
    profile = _profile("Perfil ruta", slug)
    db_session.add(profile)
    db_session.commit()

    response = client.get(f"/api/sales-profiles/slug/{slug.upper()}")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == profile.id
    assert response.json()["slug"] == slug


def test_order_and_query_resolvers_accept_same_unicode_slug_variant(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    stored_slug = f"Bót-Orden-{suffix}"
    variant = f"bÓT-ORDEN-{suffix}"
    profile = _profile("Perfil orden", stored_slug)
    db_session.add(profile)
    db_session.commit()

    resolved, legacy, resolved_id, legacy_id = resolve_sales_profile(
        db_session,
        variant,
        None,
    )
    query_resolved = resolve_sales_profile_for_query(
        db_session,
        variant,
        require_active=True,
    )

    assert resolved is not None and resolved.id == profile.id
    assert resolved_id == profile.id
    assert legacy is None and legacy_id is None
    assert query_resolved is not None and query_resolved.id == profile.id


def test_channel_monitoring_accepts_same_unicode_slug_variant(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    stored_slug = f"Bót-Canal-{suffix}"
    variant = f"bÓT-CANAL-{suffix}"
    profile = _profile("Perfil canal", stored_slug)
    db_session.add(profile)
    db_session.commit()

    payload = channel_monitoring.get_profile_audit_log(
        variant,
        db=db_session,
        hours=1,
        _ai_manager=SimpleNamespace(),
    )

    assert payload["sales_profile_slug"] == variant


def test_update_preserves_unchanged_historical_display_slug(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    canonical_slug = f"bot-historical-{suffix}"
    historical_display = f"  {canonical_slug}  "
    profile = _profile("Perfil histórico", canonical_slug)
    db_session.add(profile)
    db_session.commit()
    profile_id = int(profile.id)

    db_session.execute(
        text("UPDATE sales_profiles SET slug = :slug WHERE id = :profile_id"),
        {"slug": historical_display, "profile_id": profile_id},
    )
    db_session.commit()
    db_session.expire_all()

    updated = sales_profiles.update_sales_profile(
        profile_id,
        SalesProfileUpdate(name="Perfil histórico renombrado", slug=historical_display),
        db_session,
        SimpleNamespace(),
    )

    assert updated["slug"] == historical_display
    assert updated["name"] == "Perfil histórico renombrado"
    persisted = db_session.query(SalesProfile).filter(SalesProfile.id == profile_id).one()
    assert persisted.slug == historical_display
    assert persisted.slug_key_hash == sales_profile_slug_hash(canonical_slug)


def test_concurrent_sales_profile_create_leaves_one_normalized_slug(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    canonical = f"bót-race-{suffix}"

    results = _run_concurrent_create(
        db_session,
        (canonical, f"  BÓT-RACE-{suffix}  "),
    )

    assert sorted(status for status, _ in results) == [201, 400]
    assert any(
        "ignora mayúsculas/minúsculas" in str(detail)
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert _normalized_slug_count(db_session, canonical) == 1


def test_concurrent_sales_profile_updates_cannot_converge_on_same_slug(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    first = _profile("Perfil A", f"origen-a-{suffix}")
    second = _profile("Perfil B", f"origen-b-{suffix}")
    db_session.add_all([first, second])
    db_session.commit()
    first_id = int(first.id)
    second_id = int(second.id)

    canonical = f"bót-update-race-{suffix}"
    results = _run_concurrent_update(
        db_session,
        (first_id, second_id),
        (canonical, f"  BÓT-UPDATE-RACE-{suffix}  "),
    )

    assert sorted(status for status, _ in results) == [200, 400]
    assert any(
        "ignora mayúsculas/minúsculas" in str(detail)
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert _normalized_slug_count(db_session, canonical) == 1
    assert (
        db_session.query(SalesProfile)
        .filter(SalesProfile.id.in_([first_id, second_id]))
        .count()
        == 2
    )


def test_unrelated_sales_profile_integrity_conflict_is_not_mislabeled_as_duplicate(
    db_session: Session,
) -> None:
    error = sales_profiles._sales_profile_integrity_error(
        db_session,
        f"missing-{uuid4().hex}",
    )

    assert error.status_code == 409
    assert "integridad" in str(error.detail).lower()


def test_sales_profile_slug_migration_fails_closed_on_historical_duplicates(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "sales-profile-duplicates.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(
        engine,
        [(1, "BÓT-PERFIL"), (2, "  bót-perfil  ")],
    )
    monkeypatch.setattr(database, "engine", engine)

    try:
        with pytest.raises(
            RuntimeError,
            match="Perfiles de venta duplicados después de normalizar slug",
        ):
            run_auto_migrations()

        with engine.connect() as conn:
            slugs = conn.execute(
                text("SELECT slug FROM sales_profiles ORDER BY id")
            ).scalars().all()
            applied = {
                str(row[0])
                for row in conn.execute(text("SELECT id FROM schema_migrations"))
            }
        assert slugs == ["BÓT-PERFIL", "  bót-perfil  "]
        assert "20260825_02_sales_profile_slug_uniqueness" not in applied
    finally:
        engine.dispose()


def test_sales_profile_slug_migration_preserves_data_and_enforces_unique_hash(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "sales-profile-unique.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(
        engine,
        [(1, "  Bót-Perfil  "), (2, "otro-perfil")],
    )
    monkeypatch.setattr(database, "engine", engine)

    try:
        assert run_auto_migrations() is True
        assert run_auto_migrations() is True

        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT slug, slug_normalized, slug_key_hash "
                    "FROM sales_profiles ORDER BY id"
                )
            ).mappings().all()
            indexes = conn.execute(
                text("PRAGMA index_list('sales_profiles')")
            ).fetchall()

        assert [row["slug"] for row in rows] == ["  Bót-Perfil  ", "otro-perfil"]
        assert rows[0]["slug_normalized"] == sales_profile_slug_key("BÓT-PERFIL")
        assert rows[0]["slug_key_hash"] == sales_profile_slug_hash("bót-perfil")
        assert any(
            str(row[1]) == "ix_sales_profiles_slug_key_hash" and bool(row[2])
            for row in indexes
        )

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO sales_profiles "
                        "(id, name, slug, tipo, slug_normalized, slug_key_hash) "
                        "VALUES (3, 'Duplicado', :slug, 'bot_ia', :normalized, :digest)"
                    ),
                    {
                        "slug": "BÓT-PERFIL",
                        "normalized": sales_profile_slug_key("BÓT-PERFIL"),
                        "digest": sales_profile_slug_hash("BÓT-PERFIL"),
                    },
                )
    finally:
        engine.dispose()
