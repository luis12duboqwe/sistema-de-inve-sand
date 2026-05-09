"""
Migracion: agrega indice unico para referencias de transferencia no nulas.

Evita que dos ordenes registren la misma referencia bancaria normalizada.
Antes de crear el indice, aborta si ya existen duplicados para que produccion
pueda corregirlos conscientemente.
"""

from sqlalchemy import create_engine, inspect, text

from app.config import settings

engine = create_engine(settings.database_url)

INDEX_NAME = "uq_orders_transfer_reference_normalized_not_null"


def _duplicate_query(dialect_name: str) -> str:
    if dialect_name == "sqlite":
        return """
            SELECT transfer_reference_normalized AS ref, COUNT(*) AS count
            FROM orders
            WHERE transfer_reference_normalized IS NOT NULL
              AND TRIM(transfer_reference_normalized) != ''
            GROUP BY transfer_reference_normalized
            HAVING COUNT(*) > 1
            LIMIT 10
        """

    return """
        SELECT transfer_reference_normalized AS ref, COUNT(*) AS count
        FROM orders
        WHERE transfer_reference_normalized IS NOT NULL
          AND BTRIM(transfer_reference_normalized) != ''
        GROUP BY transfer_reference_normalized
        HAVING COUNT(*) > 1
        LIMIT 10
    """


def _create_index_sql(dialect_name: str) -> str:
    if dialect_name == "sqlite":
        return f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON orders (transfer_reference_normalized)
            WHERE transfer_reference_normalized IS NOT NULL
              AND TRIM(transfer_reference_normalized) != ''
        """

    if dialect_name == "postgresql":
        return f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON orders (transfer_reference_normalized)
            WHERE transfer_reference_normalized IS NOT NULL
              AND BTRIM(transfer_reference_normalized) != ''
        """

    return f"""
        CREATE UNIQUE INDEX {INDEX_NAME}
        ON orders (transfer_reference_normalized)
    """


def migrate() -> None:
    print("🔄 Iniciando migracion: indice unico de referencias de transferencia...")

    with engine.connect() as connection:
        inspector = inspect(engine)
        if "orders" not in inspector.get_table_names():
            print("⚠️  La tabla 'orders' no existe. Nada que migrar.")
            return

        existing_columns = {column["name"] for column in inspector.get_columns("orders")}
        if "transfer_reference_normalized" not in existing_columns:
            print("⚠️  La columna transfer_reference_normalized no existe. Ejecuta primero migrate_add_transfer_payment_fields.py")
            return

        existing_indexes = {index["name"] for index in inspector.get_indexes("orders")}
        if INDEX_NAME in existing_indexes:
            print("✅ El indice unico ya existe.")
            return

        dialect_name = connection.dialect.name
        duplicates = connection.execute(text(_duplicate_query(dialect_name))).fetchall()
        if duplicates:
            details = ", ".join(f"{row.ref} ({row.count})" for row in duplicates)
            raise RuntimeError(
                "No se puede crear el indice unico: existen referencias duplicadas. "
                f"Corrige primero estos valores: {details}"
            )

        connection.execute(text(_create_index_sql(dialect_name)))
        connection.commit()

    print("✅ Migracion completada: referencias de transferencia protegidas con indice unico.")


if __name__ == "__main__":
    migrate()
