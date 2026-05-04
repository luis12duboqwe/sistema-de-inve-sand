from typing import Dict

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from app.config import settings
import sys

engine = create_engine(settings.database_url)

PRODUCT_IMEI_COLUMNS = {
    "supplier_id": "INTEGER",
    "received_at": "TIMESTAMP",
    "sold_at": "TIMESTAMP",
    "acquisition_type": "VARCHAR(50)",
    "received_notes": "TEXT",
    "received_by": "VARCHAR(100)",
}

IMEI_HISTORY_COLUMNS = {
    "supplier_id": "INTEGER",
}


def add_missing_columns(connection: Connection, table_name: str, columns: Dict[str, str]) -> None:
    inspector = inspect(connection)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}

    for column_name, column_type in columns.items():
        if column_name in existing_columns:
            print(f"✅ {table_name}.{column_name} ya existe")
            continue

        print(f"🛠️ Agregando columna {table_name}.{column_name}...")
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def migrate() -> None:
    print("🔄 Iniciando migración: auditoría extendida de IMEIs...")

    with engine.connect() as connection:
        add_missing_columns(connection, "product_imeis", PRODUCT_IMEI_COLUMNS)
        add_missing_columns(connection, "imei_history", IMEI_HISTORY_COLUMNS)

        print("🧹 Inicializando received_at con created_at donde falte...")
        connection.execute(text("UPDATE product_imeis SET received_at = created_at WHERE received_at IS NULL"))

        print("📊 Creando índices si no existen...")
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_product_imei_supplier ON product_imeis (supplier_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_product_imei_received_at ON product_imeis (received_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_product_imei_sold_at ON product_imeis (sold_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_product_imei_acquisition_type ON product_imeis (acquisition_type)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_imei_history_supplier ON imei_history (supplier_id)"))
        connection.commit()

    print("✅ Migración completada exitosamente.")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as exc:
        print(f"❌ Error durante la migración: {exc}")
        sys.exit(1)
