import unicodedata

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text

import app.database as database
from app.models import Bank, User
from app.routers.financing import create_bank
from app.schemas import BankCreate
from app.utils.auto_migrations import run_auto_migrations
from app.utils.bank_names import bank_name_hash


DIGEST_MIGRATION_ID = "20260824_03_bank_name_digest_uniqueness"
PRE_RELEASE_MIGRATION_ID = "20260824_02_bank_name_normalized_uniqueness"


def _actor() -> User:
    return User(
        username="finance-admin",
        email="finance-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def test_create_bank_rejects_unicode17_format_control_on_python311(db_session):
    # U+13439 is Cf in Unicode 17, but Python 3.11's older Unicode table can
    # report it as Cn. The explicit Unicode-17 ranges must still reject it.
    format_control = "\U00013439"
    assert unicodedata.category(format_control) in {"Cn", "Cf"}

    with pytest.raises(HTTPException) as exc_info:
        create_bank(
            BankCreate(name=f"B{format_control}AC", active=True, normal_card_rate=0),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    assert "Unicode no permitidos" in exc_info.value.detail
    assert db_session.query(Bank).count() == 0


def test_digest_migration_runs_after_pre_release_id_was_already_recorded(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "pre_release_bank_schema.db"
    engine = create_engine(f"sqlite:///{db_path}")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE schema_migrations (
                    id VARCHAR(100) PRIMARY KEY,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        for migration_id in (
            "20260805_01_daily_close_validation",
            "20260805_02_transfer_receiving_fields",
            "20260820_01_order_completion_timestamp",
            "20260824_01_processed_message_delivery_state",
            PRE_RELEASE_MIGRATION_ID,
        ):
            conn.execute(
                text("INSERT INTO schema_migrations (id) VALUES (:migration_id)"),
                {"migration_id": migration_id},
            )

        conn.execute(
            text(
                """
                CREATE TABLE system_config (
                    id INTEGER PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    estado VARCHAR(50),
                    total NUMERIC,
                    validada_at DATETIME,
                    validated_by VARCHAR(100),
                    completed_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE stock_transfers (
                    id INTEGER PRIMARY KEY,
                    cantidad INTEGER,
                    estado VARCHAR(50),
                    received_quantity INTEGER,
                    missing_quantity INTEGER,
                    incident_notes TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE banks (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR UNIQUE NOT NULL,
                    name_normalized TEXT,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    normal_card_rate NUMERIC NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX ix_banks_name_normalized "
                "ON banks (name_normalized)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO banks (id, name, name_normalized) "
                "VALUES (1, 'BAC', 'bac')"
            )
        )

    monkeypatch.setattr(database, "engine", engine)

    try:
        assert run_auto_migrations() is True

        inspector = inspect(engine)
        bank_columns = {column["name"] for column in inspector.get_columns("banks")}
        assert "name_key_hash" in bank_columns
        bank_indexes = inspector.get_indexes("banks")
        assert any(
            index.get("name") == "ix_banks_name_key_hash" and index.get("unique")
            for index in bank_indexes
        )
        assert not any(
            index.get("name") == "ix_banks_name_normalized"
            for index in bank_indexes
        )

        with engine.connect() as conn:
            migration_ids = {
                str(row[0])
                for row in conn.execute(text("SELECT id FROM schema_migrations"))
            }
            bank_row = conn.execute(
                text("SELECT name_normalized, name_key_hash FROM banks WHERE id = 1")
            ).one()

        assert PRE_RELEASE_MIGRATION_ID in migration_ids
        assert DIGEST_MIGRATION_ID in migration_ids
        assert tuple(bank_row) == ("bac", bank_name_hash("BAC"))
    finally:
        engine.dispose()
