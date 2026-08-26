from concurrent.futures import ThreadPoolExecutor
from time import sleep

from sqlalchemy import create_engine, inspect, text

import app.database as database
import app.utils.auto_migrations as auto_migrations
from app.startup_schema_lock import startup_schema_lock


def _create_legacy_sqlite_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE orders ("
                "id INTEGER PRIMARY KEY, estado VARCHAR(50), total NUMERIC)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE stock_transfers ("
                "id INTEGER PRIMARY KEY, cantidad INTEGER, estado VARCHAR(50))"
            )
        )


def test_startup_schema_lock_serializes_concurrent_sqlite_migrations(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "concurrent-startup.db"
    engine = create_engine(f"sqlite:///{db_path}")
    _create_legacy_sqlite_schema(engine)
    monkeypatch.setattr(database, "engine", engine)

    original_add_column = auto_migrations._add_column_if_missing

    def deliberately_slow_add_column(table: str, column: str, column_type: str) -> None:
        # Amplify the check-then-ALTER race that exists without startup serialization.
        sleep(0.03)
        original_add_column(table, column, column_type)

    monkeypatch.setattr(
        auto_migrations,
        "_add_column_if_missing",
        deliberately_slow_add_column,
    )

    def start_worker() -> bool:
        with startup_schema_lock():
            return auto_migrations.run_auto_migrations()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: start_worker(), range(2)))

        assert results == [True, True]

        order_columns = {
            column["name"] for column in inspect(engine).get_columns("orders")
        }
        transfer_columns = {
            column["name"] for column in inspect(engine).get_columns("stock_transfers")
        }
        assert {"validada_at", "validated_by", "completed_at"} <= order_columns
        assert {"received_quantity", "missing_quantity", "incident_notes"} <= transfer_columns

        with engine.connect() as conn:
            applied = conn.execute(
                text("SELECT id, COUNT(*) FROM schema_migrations GROUP BY id")
            ).all()
        assert applied
        assert all(int(count) == 1 for _, count in applied)
    finally:
        engine.dispose()
