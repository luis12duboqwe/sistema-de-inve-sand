import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from upgrade_audit import _sqlite_engine, build_snapshot, compare_snapshots


TEST_KEY = b"upgrade-audit-test-key-32-bytes!!"
OTHER_TEST_KEY = b"another-upgrade-audit-key-32bytes!"

SCHEMA = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL,
    activo BOOLEAN NOT NULL
);
CREATE TABLE stock (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    cantidad_disponible INTEGER NOT NULL,
    cantidad_reservada INTEGER NOT NULL,
    cantidad_defectuosa INTEGER NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    total NUMERIC(10, 2) NOT NULL
);
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL
);
CREATE TABLE product_imeis (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    imei TEXT NOT NULL,
    vendido BOOLEAN NOT NULL
);
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    is_superuser BOOLEAN NOT NULL
);
CREATE TABLE stock_transfers (
    id INTEGER PRIMARY KEY,
    cantidad INTEGER NOT NULL,
    received_quantity INTEGER,
    missing_quantity INTEGER
);
"""


def _seed_database(path: Path, *, extra_table: bool = False, legacy_column: bool = False) -> None:
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        for statement in SCHEMA.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        if legacy_column:
            conn.execute(text("ALTER TABLE products ADD COLUMN legacy_note TEXT"))
        conn.execute(text("INSERT INTO products (id, sku, activo) VALUES (1, 'PHONE-1', 1), (2, 'PHONE-2', 0)"))
        if legacy_column:
            conn.execute(text("UPDATE products SET legacy_note='historical-value' WHERE id=1"))
        conn.execute(text("INSERT INTO stock VALUES (1, 1, 5, 2, 1), (2, 2, 3, 0, 0)"))
        conn.execute(text("INSERT INTO orders VALUES (1, 'Persona Privada', 1250.50)"))
        conn.execute(text("INSERT INTO order_items VALUES (1, 1, 1, 2)"))
        conn.execute(text("INSERT INTO product_imeis VALUES (1, 1, 'SECRET-IMEI-1', 0), (2, 1, 'SECRET-IMEI-2', 1)"))
        conn.execute(text("INSERT INTO users VALUES (1, 'private-user', 'SECRET-HASH', 1, 1)"))
        conn.execute(text("INSERT INTO stock_transfers VALUES (1, 4, 3, 1)"))
        if extra_table:
            conn.execute(text("CREATE TABLE future_feature (id INTEGER PRIMARY KEY)"))
    engine.dispose()


def _snapshot(path: Path, key: bytes = TEST_KEY):
    engine = _sqlite_engine(path)
    try:
        return build_snapshot(engine, key)
    finally:
        engine.dispose()


def test_snapshot_contains_counts_aggregates_and_fingerprints_without_row_level_data(tmp_path):
    database_path = tmp_path / "inventory.db"
    _seed_database(database_path)

    snapshot = _snapshot(database_path)

    assert snapshot["health"]["ok"] is True
    assert snapshot["tables"]["products"]["rows"] == 2
    assert snapshot["critical"]["products"]["active_rows"] == 1
    assert snapshot["critical"]["stock"]["available_total"] == 8
    assert snapshot["critical"]["stock"]["reserved_total"] == 2
    assert snapshot["critical"]["stock"]["defective_total"] == 1
    assert snapshot["critical"]["orders"]["amount_total"] == "1250.5"
    assert snapshot["critical"]["product_imeis"]["sold_rows"] == 1
    assert snapshot["critical"]["product_imeis"]["unsold_rows"] == 1
    assert snapshot["critical"]["users"]["active_rows"] == 1
    assert snapshot["critical"]["users"]["superuser_rows"] == 1
    assert len(snapshot["tables"]["users"]["fingerprints"]["hashed_password"]) == 64
    assert snapshot["fingerprint"]["key_id"]

    serialized = json.dumps(snapshot)
    assert "Persona Privada" not in serialized
    assert "SECRET-IMEI" not in serialized
    assert "private-user" not in serialized
    assert "SECRET-HASH" not in serialized
    assert TEST_KEY.hex() not in serialized


def test_compare_allows_new_schema_tables_but_requires_source_data_counts(tmp_path):
    before_path = tmp_path / "before.db"
    after_path = tmp_path / "after.db"
    _seed_database(before_path)
    _seed_database(after_path, extra_table=True)

    report = compare_snapshots(_snapshot(before_path), _snapshot(after_path))
    assert report["compatible"] is True
    assert report["mismatches"] == []
    assert any("future_feature" in warning for warning in report["warnings"])


def test_compare_detects_lost_rows_and_critical_total_changes(tmp_path):
    before_path = tmp_path / "before.db"
    after_path = tmp_path / "after.db"
    _seed_database(before_path)
    _seed_database(after_path)

    engine = create_engine(f"sqlite:///{after_path}")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM product_imeis WHERE id = 2"))
        conn.execute(text("UPDATE stock SET cantidad_disponible = 1 WHERE id = 1"))
    engine.dispose()

    report = compare_snapshots(_snapshot(before_path), _snapshot(after_path))
    assert report["compatible"] is False
    assert any("product_imeis" in mismatch for mismatch in report["mismatches"])
    assert any("stock.available_total" in mismatch for mismatch in report["mismatches"])


def test_compare_detects_content_corruption_even_when_counts_and_aggregates_match(tmp_path):
    before_path = tmp_path / "before.db"
    after_path = tmp_path / "after.db"
    _seed_database(before_path)
    _seed_database(after_path)

    engine = create_engine(f"sqlite:///{after_path}")
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET hashed_password='CORRUPTED-HASH' WHERE id=1"))
        conn.execute(text("UPDATE orders SET customer_name='Otro Nombre' WHERE id=1"))
    engine.dispose()

    report = compare_snapshots(_snapshot(before_path), _snapshot(after_path))
    assert report["compatible"] is False
    assert "Contenido distinto: users.hashed_password" in report["mismatches"]
    assert "Contenido distinto: orders.customer_name" in report["mismatches"]


def test_compare_rejects_loss_of_legacy_source_column(tmp_path):
    before_path = tmp_path / "before.db"
    after_path = tmp_path / "after.db"
    _seed_database(before_path, legacy_column=True)
    _seed_database(after_path)

    report = compare_snapshots(_snapshot(before_path), _snapshot(after_path))
    assert report["compatible"] is False
    assert "Falta columna destino con datos históricos: products.legacy_note" in report["mismatches"]


def test_compare_requires_same_private_fingerprint_key(tmp_path):
    before_path = tmp_path / "before.db"
    after_path = tmp_path / "after.db"
    _seed_database(before_path)
    _seed_database(after_path)

    with pytest.raises(ValueError, match="misma clave"):
        compare_snapshots(_snapshot(before_path, TEST_KEY), _snapshot(after_path, OTHER_TEST_KEY))


def test_snapshot_supports_real_postgresql_test_engine(db_session):
    engine = db_session.get_bind()
    assert engine.dialect.name == "postgresql"

    snapshot = build_snapshot(engine, TEST_KEY)

    assert snapshot["health"] == {"check": "connectivity", "ok": True, "result": "ok"}
    assert snapshot["source"]["dialect"] == "postgresql"
    assert "products" in snapshot["tables"]
    assert "stock" in snapshot["tables"]
    assert "orders" in snapshot["tables"]
    assert "password" not in snapshot["source"]
    assert "host" not in snapshot["source"]


def test_content_fingerprints_match_between_sqlite_and_real_postgresql(tmp_path, db_session):
    sqlite_path = tmp_path / "cross-engine.db"
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE upgrade_audit_cross_engine ("
                "id INTEGER PRIMARY KEY, active BOOLEAN NOT NULL, "
                "amount NUMERIC(10, 2) NOT NULL, note TEXT)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO upgrade_audit_cross_engine (id, active, amount, note) "
                "VALUES (1, 1, 1250.50, 'same-value'), (2, 0, 9, NULL)"
            )
        )

    postgres_engine = db_session.get_bind()
    with postgres_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS upgrade_audit_cross_engine"))
        conn.execute(
            text(
                "CREATE TABLE upgrade_audit_cross_engine ("
                "id INTEGER PRIMARY KEY, active BOOLEAN NOT NULL, "
                "amount NUMERIC(10, 2) NOT NULL, note TEXT)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO upgrade_audit_cross_engine (id, active, amount, note) "
                "VALUES (1, TRUE, 1250.50, 'same-value'), (2, FALSE, 9, NULL)"
            )
        )

    try:
        before = build_snapshot(sqlite_engine, TEST_KEY)
        after = build_snapshot(postgres_engine, TEST_KEY)
        report = compare_snapshots(before, after)
        assert report["compatible"] is True
        assert report["mismatches"] == []
    finally:
        sqlite_engine.dispose()
        with postgres_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS upgrade_audit_cross_engine"))
