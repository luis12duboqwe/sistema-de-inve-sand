from sqlalchemy import inspect, text

import app.database as database
from app.utils.auto_migrations import MIGRATIONS, run_auto_migrations


def test_versioned_auto_migrations_are_recorded_and_idempotent():
    assert database.engine.dialect.name == "postgresql"

    assert run_auto_migrations() is True
    assert run_auto_migrations() is True

    expected_ids = {migration_id for migration_id, _ in MIGRATIONS}
    with database.engine.connect() as conn:
        recorded_ids = {
            str(row[0])
            for row in conn.execute(text("SELECT id FROM schema_migrations"))
        }

    assert expected_ids.issubset(recorded_ids)

    inspector = inspect(database.engine)
    order_columns = {column["name"] for column in inspector.get_columns("orders")}
    transfer_columns = {
        column["name"] for column in inspector.get_columns("stock_transfers")
    }

    assert {"validada_at", "validated_by"}.issubset(order_columns)
    assert {
        "received_quantity",
        "missing_quantity",
        "incident_notes",
    }.issubset(transfer_columns)
