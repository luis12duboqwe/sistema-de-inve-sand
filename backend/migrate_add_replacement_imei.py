"""
Migración: Agrega columna replacement_imei a return_items.

Esta columna almacena el IMEI del equipo de reemplazo que sale al cliente
en un cambio por garantía (action='warranty_exchange').
"""
from sqlalchemy import create_engine, text
from sqlalchemy import inspect
from app.config import settings

engine = create_engine(settings.database_url)


def migrate():
    print("🔄 Iniciando migración: Agregar columna replacement_imei a return_items...")

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        if "return_items" not in existing_tables:
            print("⚠️  La tabla 'return_items' no existe. Ejecuta migrate_add_returns.py primero.")
            return

        # Verificar si la columna ya existe
        columns = {c["name"] for c in inspector.get_columns("return_items")}
        if "replacement_imei" in columns:
            print("✅ La columna 'replacement_imei' ya existe en 'return_items'. Nada que hacer.")
            return

        print("🛠️  Agregando columna 'replacement_imei' a 'return_items'...")
        conn.execute(text("ALTER TABLE return_items ADD COLUMN replacement_imei VARCHAR"))
        conn.commit()

        print("✅ Migración completada: columna replacement_imei agregada correctamente.")
        print("   Uso: IMEI del equipo de reemplazo enviado al cliente en cambios por garantía.")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        raise
