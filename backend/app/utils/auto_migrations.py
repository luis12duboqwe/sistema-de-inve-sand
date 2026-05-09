"""
Automatic database migrations on startup.

Verifies and applies necessary schema updates without manual intervention.
"""

import logging

logger = logging.getLogger(__name__)


def _apply_daily_close_migration():
    """Agrega columnas de cierre de día a orders y crea tabla system_config."""
    try:
        from app.database import engine
        from sqlalchemy import text, inspect

        inspector = inspect(engine)

        with engine.connect() as conn:
            # ── Tabla system_config ─────────────────────────────────────────
            if "system_config" not in inspector.get_table_names():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS system_config (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(100) UNIQUE NOT NULL,
                        value TEXT,
                        description VARCHAR(255),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_by VARCHAR(100)
                    )
                """))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_system_config_key ON system_config (key)"
                ))
                logger.info("Auto-migration: tabla system_config creada.")

            # ── Columnas en orders ──────────────────────────────────────────
            existing_cols = [c["name"] for c in inspector.get_columns("orders")]

            if "validada_at" not in existing_cols:
                conn.execute(text(
                    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS validada_at TIMESTAMP WITH TIME ZONE"
                ))
                logger.info("Auto-migration: columna validada_at agregada a orders.")

            if "validated_by" not in existing_cols:
                conn.execute(text(
                    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS validated_by VARCHAR(100)"
                ))
                logger.info("Auto-migration: columna validated_by agregada a orders.")

            conn.commit()

    except Exception as e:
        logger.warning("Auto-migration daily_close no crítica, continuando: %s", e)


def _apply_transfer_receiving_fields_migration():
    """Agrega columnas de recepción parcial a stock_transfers si faltan."""
    try:
        from app.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE stock_transfers ADD COLUMN IF NOT EXISTS received_quantity INTEGER"
            ))
            conn.execute(text(
                "ALTER TABLE stock_transfers ADD COLUMN IF NOT EXISTS missing_quantity INTEGER"
            ))
            conn.execute(text(
                "ALTER TABLE stock_transfers ADD COLUMN IF NOT EXISTS incident_notes TEXT"
            ))
            conn.commit()

        logger.info("Auto-migration: columnas de recepción parcial en stock_transfers verificadas.")
    except Exception as e:
        logger.warning("Auto-migration stock_transfers no crítica, continuando: %s", e)


def run_auto_migrations():
    """
    Execute auto-migrations script if database exists.
    Called during app startup.
    """
    logger.info("Ejecutando auto-migraciones al iniciar...")
    _apply_daily_close_migration()
    _apply_transfer_receiving_fields_migration()
    logger.info("Auto-migraciones completadas.")
    return True

