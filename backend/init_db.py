"""
Script de inicialización de la base de datos V2.0.

Este script crea las tablas necesarias y opcionalmente puebla la base de datos
con datos de ejemplo compatibles con el sistema multi-ubicación.

Uso:
    python init_db.py              # Solo crea las tablas
    python init_db.py --with-data  # Crea las tablas y datos V2.0 de ejemplo
"""

import argparse
import sys

from app import models as _models  # noqa: F401 - fuerza registro de todos los modelos en metadata
from app.database import Base
from app.database import SessionLocal, engine
from app.utils.demo_seed import seed_demo_data


def init_database():
    """Crea todas las tablas en la base de datos."""
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tablas creadas exitosamente")


def insert_sample_data():
    """Inserta datos de ejemplo V2.0 en la base de datos."""
    db = SessionLocal()

    try:
        print("\n" + "=" * 70)
        print("INICIALIZANDO SISTEMA V2.0 - DATOS DE PRUEBA")
        print("=" * 70)

        summary = seed_demo_data(db, created_by="init_db.py")

        print("=" * 70)
        print("✅ BASE DE DATOS V2.0 INICIALIZADA EXITOSAMENTE")
        print("=" * 70)
        print(f"\n📍 Ubicaciones creadas: {summary['locations_created']}")
        print(f"🤖 Perfiles de venta creados: {summary['sales_profiles_created']}")
        print(f"🧩 Profiles legacy creados: {summary['profiles_created']}")
        print(f"📦 Productos globales creados: {summary['products_created']}")
        print(f"📈 Stocks creados: {summary['stock_rows_created']}")
        print(f"🔁 Stocks actualizados: {summary['stock_rows_updated']}")
        print(f"📱 IMEIs creados: {summary['imeis_created']}")
        print(f"🧾 Órdenes demo creadas: {summary['orders_created']}")

        print("\n🔗 API Endpoints disponibles:")
        print("   - http://localhost:8000/docs (Swagger UI)")
        print("   - GET /api/locations (Ver ubicaciones)")
        print("   - GET /api/sales-profiles (Ver perfiles de venta)")
        print("   - GET /api/products (Ver productos con stock total)")
        print("   - GET /api/orders (Ver órdenes de prueba)")
        print("   - POST /api/orders (Crear orden especificando ubicación origen)")
        print("=" * 70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error al insertar datos: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Inicializa la base de datos del sistema de inventario")
    parser.add_argument("--with-data", action="store_true", help="Inserta datos de ejemplo además de crear las tablas")

    args = parser.parse_args()

    print("=" * 60)
    print("INICIALIZACIÓN DE BASE DE DATOS")
    print("=" * 60)

    init_database()

    if args.with_data:
        insert_sample_data()
    else:
        print("\nPara insertar datos de ejemplo, ejecuta:")
        print("  python init_db.py --with-data")
        print("\nO usa el endpoint POST /api/init-data")

    print()


if __name__ == "__main__":
    main()
