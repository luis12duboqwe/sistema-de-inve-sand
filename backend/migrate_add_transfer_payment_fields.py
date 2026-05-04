"""
Migración: agrega campos para transferencias bancarias en órdenes.

Campos nuevos en `orders`:
- transfer_bank_name
- transfer_reference
- transfer_reference_normalized
"""

from sqlalchemy import create_engine, inspect, text
from app.config import settings

engine = create_engine(settings.database_url)


def migrate() -> None:
    print("🔄 Iniciando migración: campos de transferencia en órdenes...")

    with engine.connect() as connection:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        if "orders" not in table_names:
            print("⚠️  La tabla 'orders' no existe. Nada que migrar.")
            return

        existing_columns = {column["name"] for column in inspector.get_columns("orders")}

        if "transfer_bank_name" not in existing_columns:
            print("🛠️  Agregando columna transfer_bank_name...")
            connection.execute(text("ALTER TABLE orders ADD COLUMN transfer_bank_name VARCHAR(120)"))

        if "transfer_reference" not in existing_columns:
            print("🛠️  Agregando columna transfer_reference...")
            connection.execute(text("ALTER TABLE orders ADD COLUMN transfer_reference VARCHAR(120)"))

        if "transfer_reference_normalized" not in existing_columns:
            print("🛠️  Agregando columna transfer_reference_normalized...")
            connection.execute(text("ALTER TABLE orders ADD COLUMN transfer_reference_normalized VARCHAR(120)"))

        # Índices (best-effort, ignora si ya existen)
        try:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_transfer_bank_name ON orders (transfer_bank_name)"))
        except Exception:
            pass

        try:
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_transfer_reference_normalized ON orders (transfer_reference_normalized)"))
        except Exception:
            pass

        connection.commit()

    print("✅ Migración completada: campos de transferencia agregados.")


if __name__ == "__main__":
    migrate()
