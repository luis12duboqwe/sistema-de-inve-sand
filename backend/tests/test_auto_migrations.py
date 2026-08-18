from sqlalchemy import inspect, text

import app.database as database
from app.utils.auto_migrations import MIGRATIONS, run_auto_migrations


def test_versioned_auto_migrations_are_recorded_and_idempotent(db_session, monkeypatch):
    # test_api_usage.py levanta un servidor real con un engine/esquema temporal.
    # Esta prueba debe validar las migraciones contra el engine aislado de su
    # propia fixture, no contra cualquier engine global dejado por otro módulo.
    test_engine = db_session.get_bind()
    monkeypatch.setattr(database, "engine", test_engine)

    assert test_engine.dialect.name == "postgresql"

    assert run_auto_migrations() is True
    assert run_auto_migrations() is True

    expected_ids = {migration_id for migration_id, _ in MIGRATIONS}
    with test_engine.connect() as conn:
        recorded_ids = {
            str(row[0])
            for row in conn.execute(text("SELECT id FROM schema_migrations"))
        }

    assert expected_ids.issubset(recorded_ids)

    inspector = inspect(test_engine)
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
