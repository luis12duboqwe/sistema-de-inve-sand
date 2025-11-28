"""
Script de inicialización de la base de datos.

Este script crea las tablas necesarias y opcionalmente puebla la base de datos
con datos de ejemplo para testing.

Uso:
    python init_db.py              # Solo crea las tablas
    python init_db.py --with-data  # Crea las tablas y datos de ejemplo
"""

import sys
import argparse
from app.database import engine, SessionLocal
from app.models import Base, Profile, Product, Stock


def init_database():
    """Crea todas las tablas en la base de datos."""
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tablas creadas exitosamente")


def insert_sample_data():
    """
    Inserta datos de ejemplo en la base de datos.
    
    Crea:
    - 1 perfil: Softmobile
    - 4 productos: 2 celulares y 2 accesorios
    - Stock inicial para cada producto
    """
    db = SessionLocal()
    
    try:
        existing_profile = db.query(Profile).filter(Profile.slug == "softmobile").first()
        if existing_profile:
            print("⚠ Los datos de ejemplo ya existen. Saltando inserción...")
            return
        
        print("\nInsertando datos de ejemplo...")
        
        profile = Profile(
            name="Softmobile",
            slug="softmobile",
            active=True
        )
        db.add(profile)
        db.flush()
        print(f"✓ Perfil creado: {profile.name} (slug: {profile.slug})")
        
        products_data = [
            {
                "sku": "SM-S24-256-NEGRO-NUEVO",
                "nombre": "Samsung Galaxy S24 256GB Negro",
                "categoria": "celular",
                "marca": "Samsung",
                "modelo": "Galaxy S24",
                "capacidad": "256GB",
                "condicion": "nuevo",
                "precio": 18500.00,
                "garantia_meses": 12,
                "stock": 5
            },
            {
                "sku": "IP-15PRO-512-TITANIO-NUEVO",
                "nombre": "iPhone 15 Pro 512GB Titanio",
                "categoria": "celular",
                "marca": "Apple",
                "modelo": "iPhone 15 Pro",
                "capacidad": "512GB",
                "condicion": "nuevo",
                "precio": 35000.00,
                "garantia_meses": 12,
                "stock": 3
            },
            {
                "sku": "ACC-FUNDA-SILICONA-UNIVERSAL",
                "nombre": "Funda de Silicona Universal",
                "categoria": "accesorio",
                "marca": "Genérico",
                "modelo": "Universal",
                "capacidad": None,
                "condicion": "nuevo",
                "precio": 150.00,
                "garantia_meses": 0,
                "stock": 50
            },
            {
                "sku": "ACC-CARGADOR-RAPIDO-20W",
                "nombre": "Cargador Rápido 20W USB-C",
                "categoria": "accesorio",
                "marca": "Anker",
                "modelo": "PowerPort 20W",
                "capacidad": "20W",
                "condicion": "nuevo",
                "precio": 350.00,
                "garantia_meses": 6,
                "stock": 25
            }
        ]
        
        print("\nCreando productos:")
        for product_data in products_data:
            stock_qty = product_data.pop("stock")
            
            product = Product(
                profile_id=profile.id,
                **product_data,
                moneda="HNL",
                activo=True
            )
            db.add(product)
            db.flush()
            
            stock = Stock(
                product_id=product.id,
                cantidad_disponible=stock_qty
            )
            db.add(stock)
            
            print(f"  ✓ {product.nombre} - Stock: {stock_qty} unidades")
        
        db.commit()
        print(f"\n✓ {len(products_data)} productos creados exitosamente")
        print("\n" + "="*60)
        print("Base de datos inicializada con éxito!")
        print("="*60)
        print("\nPuedes probar la API en: http://localhost:8000/docs")
        print(f"Perfil de prueba: {profile.slug}")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error al insertar datos: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Inicializa la base de datos del sistema de inventario"
    )
    parser.add_argument(
        "--with-data",
        action="store_true",
        help="Inserta datos de ejemplo además de crear las tablas"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("INICIALIZACIÓN DE BASE DE DATOS")
    print("="*60)
    
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
