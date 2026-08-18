import json
from pathlib import Path

from sqlalchemy import create_engine, text

from upgrade_audit import _sqlite_engine, build_snapshot, compare_snapshots


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


def _seed_database(path: Path, *, extra_table: bool = False) -> None:
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        for statement in SCHEMA.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.execute(text("INSERT INTO products VALUES (1, 'PHONE-1', 1), (2, 'PHONE-2', 0)"))
        conn.execute(text("INSERT INTO stock VALUES (1, 1, 5, 2, 1), (2, 2, 3, 0, 0)"))
        conn.execute(text("INSERT INTO orders VALUES (1, 'Persona Privada', 1250.50)"))
        conn.execute(text("INSERT INTO order_items VALUES (1, 1, 1, 2)"))
        conn.execute(text("INSERT INTO product_imeis VALUES (1, 1, 'SECRET-IMEI-1', 0), (2, 1, 'SECRET-IMEI-2', 1)"))
        conn.execute(text("INSERT INTO users VALUES (1, 'private-user', 'SECRET-HASH', 1, 1)"))
        conn.execute(text("INSERT INTO stock_transfers VALUES (1, 4, 3, 1)"))
        if extra_table:
            conn.execute(text("CREATE TABLE future_feature (id INTEGER PRIMARY KEY)"))
    engine.dispose()


def test_snapshot_contains_counts_and_aggregates_without_row_level_data(tmp_path):
    database_path = tmp_path / "inventory.db"
    _seed_database(database_path)

    engine = _sqlite_engine(database_path)
    try:
        snapshot = build_snapshot(engine)
    finally:
        engine.dispose()

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

    serialized = json.dumps(snapshot)
    assert "Persona Privada" not in serialized
    assert "SECRET-IMEI" not in serialized
    assert "private-user" not in serialized
    assert "SECRET-HASH" not in serialized


def test_compare_allows_new_empty_schema_tables_but_requires_source_data_counts(tmp_path):
    before_path = tmp_path / "before.db"
    after_path = tmp_path / "after.db"
    _seed_database(before_path)
    _seed_database(after_path, extra_table=True)

    before_engine = _sqlite_engine(before_path)
    after_engine = _sqlite_engine(after_path)
    try:
        before = build_snapshot(before_engine)
        after = build_snapshot(after_engine)
    finally:
        before_engine.dispose()
        after_engine.dispose()

    report = compare_snapshots(before, after)
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

    before_engine = _sqlite_engine(before_path)
    after_engine = _sqlite_engine(after_path)
    try:
        before = build_snapshot(before_engine)
        after = build_snapshot(after_engine)
    finally:
        before_engine.dispose()
        after_engine.dispose()

    report = compare_snapshots(before, after)
    assert report["compatible"] is False
    assert any("product_imeis" in mismatch for mismatch in report["mismatches"])
    assert any("stock.available_total" in mismatch for mismatch in report["mismatches"])


def test_snapshot_supports_real_postgresql_test_engine(db_session):
    engine = db_session.get_bind()
    assert engine.dialect.name == "postgresql"

    snapshot = build_snapshot(engine)

    assert snapshot["health"] == {"check": "connectivity", "ok": True, "result": "ok"}
    assert snapshot["source"]["dialect"] == "postgresql"
    assert "products" in snapshot["tables"]
    assert "stock" in snapshot["tables"]
    assert "orders" in snapshot["tables"]
    assert "password" not in snapshot["source"]
    assert "host" not in snapshot["source"]
