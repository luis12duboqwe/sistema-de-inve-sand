from sqlalchemy import create_engine, inspect, text

import app.database as database
from app.utils.auto_migrations import MIGRATIONS, run_auto_migrations


def _recorded_migration_ids(engine) -> set[str]:
    with engine.connect() as conn:
        return {
            str(row[0])
            for row in conn.execute(text("SELECT id FROM schema_migrations"))
        }


def _assert_critical_upgrade_columns(engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
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

    if "processed_messages" in table_names:
        processed_columns = {
            column["name"] for column in inspector.get_columns("processed_messages")
        }
        assert {"delivery_status", "reply_text"}.issubset(processed_columns)


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
    assert expected_ids.issubset(_recorded_migration_ids(test_engine))
    _assert_critical_upgrade_columns(test_engine)


def test_legacy_sqlite_database_is_upgraded_without_data_loss(tmp_path, monkeypatch):
    db_path = tmp_path / "inventory.db"
    test_engine = create_engine(f"sqlite:///{db_path}")

    # Simula una instalación usada antes de que existieran los campos actuales.
    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    estado VARCHAR(50),
                    total NUMERIC
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
                    estado VARCHAR(50)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE processed_messages (
                    id INTEGER PRIMARY KEY,
                    message_id VARCHAR UNIQUE NOT NULL,
                    channel VARCHAR NOT NULL,
                    customer_phone VARCHAR,
                    sales_profile_id INTEGER,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    expires_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO orders (id, estado, total) "
                "VALUES (41, 'completada', 12500)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO stock_transfers (id, cantidad, estado) "
                "VALUES (7, 3, 'pendiente')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO processed_messages (id, message_id, channel, expires_at) "
                "VALUES (3, 'legacy-message', 'whatsapp', '2030-01-01 00:00:00')"
            )
        )

    monkeypatch.setattr(database, "engine", test_engine)

    assert run_auto_migrations() is True
    assert run_auto_migrations() is True

    expected_ids = {migration_id for migration_id, _ in MIGRATIONS}
    assert expected_ids.issubset(_recorded_migration_ids(test_engine))
    _assert_critical_upgrade_columns(test_engine)

    with test_engine.connect() as conn:
        order = conn.execute(
            text("SELECT id, estado, total FROM orders WHERE id = 41")
        ).one()
        transfer = conn.execute(
            text(
                "SELECT id, cantidad, estado FROM stock_transfers WHERE id = 7"
            )
        ).one()
        processed = conn.execute(
            text(
                "SELECT message_id, channel, delivery_status, reply_text "
                "FROM processed_messages WHERE id = 3"
            )
        ).one()

    assert tuple(order) == (41, "completada", 12500)
    assert tuple(transfer) == (7, 3, "pendiente")
    assert tuple(processed) == ("legacy-message", "whatsapp", None, None)

    # La primera migración sobre un SQLite real crea una copia consistente antes
    # de tocar el esquema. La segunda ejecución no genera backups redundantes.
    backups = sorted((tmp_path / "backups").glob("inventory.pre-migration-*.db"))
    assert len(backups) == 1

    backup_engine = create_engine(f"sqlite:///{backups[0]}")
    try:
        backup_inspector = inspect(backup_engine)
        backup_order_columns = {
            column["name"] for column in backup_inspector.get_columns("orders")
        }
        backup_processed_columns = {
            column["name"] for column in backup_inspector.get_columns("processed_messages")
        }
        assert "validada_at" not in backup_order_columns
        assert "validated_by" not in backup_order_columns
        assert "delivery_status" not in backup_processed_columns
        assert "reply_text" not in backup_processed_columns

        with backup_engine.connect() as conn:
            backed_up_order = conn.execute(
                text("SELECT id, estado, total FROM orders WHERE id = 41")
            ).one()
            backed_up_message = conn.execute(
                text("SELECT message_id, channel FROM processed_messages WHERE id = 3")
            ).one()
        assert tuple(backed_up_order) == (41, "completada", 12500)
        assert tuple(backed_up_message) == ("legacy-message", "whatsapp")
    finally:
        backup_engine.dispose()
        test_engine.dispose()
