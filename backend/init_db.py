"""
Script de inicialización de la base de datos V2.0.

Este script crea las tablas necesarias y opcionalmente puebla la base de datos
con datos de ejemplo compatibles con el sistema multi-ubicación.

Uso:
    python init_db.py              # Solo crea las tablas
    python init_db.py --with-data  # Crea las tablas y datos V2.0 de ejemplo
"""

import sys
import argparse
import json
from app.database import engine, SessionLocal
from app.models import Base, Location, SalesProfile, Product, Stock, Profile


def init_database():
    """Crea todas las tablas en la base de datos."""
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tablas creadas exitosamente")


def insert_sample_data():
    """
    Inserta datos de ejemplo V2.0 en la base de datos.
    
    Crea:
    - 3 Ubicaciones: Tienda Centro, Tienda Norte, Bodega Central
    - 2 Perfiles de Venta: Bot WhatsApp Principal, Vendedor Tienda
    - 1 Profile Legacy (compatibilidad): Softmobile
    - 4 productos globales: 2 celulares y 2 accesorios
    - Stock distribuido en múltiples ubicaciones
    """
    db = SessionLocal()
    
    try:
        # Verificar si ya existen datos V2.0
        existing_location = db.query(Location).first()
        if existing_location:
            print("⚠ Los datos de ejemplo V2.0 ya existen. Saltando inserción...")
            return
        
        print("\n" + "="*70)
        print("INICIALIZANDO SISTEMA V2.0 - MULTI-UBICACIÓN")
        print("="*70)
        
        # ========== 1. CREAR UBICACIONES FÍSICAS ==========
        print("\n[1/5] Creando ubicaciones físicas...")
        locations_data = [
            {"nombre": "Tienda Centro", "tipo": "tienda", "direccion": "Av. Principal #123, Centro", "telefono": "+504 2234-5678"},
            {"nombre": "Tienda Norte", "tipo": "tienda", "direccion": "Col. Las Minitas, Salida Norte", "telefono": "+504 2245-6789"},
            {"nombre": "Bodega Central", "tipo": "bodega", "direccion": "Zona Industrial, Bodega #5", "telefono": "+504 2256-7890"}
        ]
        
        locations = []
        for loc_data in locations_data:
            location = Location(**loc_data, activo=True)
            db.add(location)
            db.flush()
            locations.append(location)
            print(f"  ✓ {location.nombre} ({location.tipo})")
        
        # ========== 2. CREAR PERFILES DE VENTA ==========
        print("\n[2/5] Creando perfiles de venta...")
        
        # Configuración de negociación para el Bot
        bot_config = {
            "numero": "+504 9999-8888",
            "horario": "24/7",
            "auto_respuesta": True,
            "negotiation_rules": {
                "max_discount_percent": 0.05,
                "steps": [0.02, 0.04, 0.05],
                "round_to": 100,
                "gift_policy": "strict_tradeoff"  # Si descuento > 2%, quitar regalos
            }
        }
        
        sales_profiles_data = [
            {
                "name": "Bot WhatsApp Principal",
                "slug": "bot-whatsapp-1",
                "tipo": "bot_ia",
                "canales": '["whatsapp"]',
                "configuracion": json.dumps(bot_config)
            },
            {
                "name": "Vendedor Tienda Centro",
                "slug": "vendedor-centro",
                "tipo": "vendedor_humano",
                "canales": '["whatsapp", "facebook"]',
                "configuracion": '{"turno": "8AM-6PM", "comision": 5}'
            }
        ]
        
        sales_profiles = []
        for sp_data in sales_profiles_data:
            sales_profile = SalesProfile(**sp_data, active=True)
            db.add(sales_profile)
            db.flush()
            sales_profiles.append(sales_profile)
            print(f"  ✓ {sales_profile.name} ({sales_profile.tipo})")
        
        # ========== 3. CREAR PROFILE LEGACY (Compatibilidad) ==========
        print("\n[3/5] Creando profile legacy (compatibilidad V1)...")
        profile = Profile(
            name="Softmobile",
            slug="softmobile",
            active=True
        )
        db.add(profile)
        db.flush()
        print(f"  ✓ {profile.name} (slug: {profile.slug}) - LEGACY V1")
        
        # ========== 4. CREAR PRODUCTOS GLOBALES ==========
        print("\n[4/5] Creando productos globales...")
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
                # Stock distribuido: Tienda Centro: 3, Tienda Norte: 2, Bodega: 5
                "stock_distribution": [3, 2, 5]
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
                # Stock distribuido: Tienda Centro: 1, Tienda Norte: 1, Bodega: 3
                "stock_distribution": [1, 1, 3]
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
                # Stock distribuido: Tienda Centro: 20, Tienda Norte: 15, Bodega: 50
                "stock_distribution": [20, 15, 50]
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
                # Stock distribuido: Tienda Centro: 10, Tienda Norte: 8, Bodega: 25
                "stock_distribution": [10, 8, 25]
            }
        ]
        
        products = []
        stock_distributions = []
        for product_data in products_data:
            stock_distribution = product_data.get("stock_distribution", [])
            stock_distributions.append(stock_distribution)

            # Evitar mutar products_data: copiar sin stock_distribution
            product_fields = {k: v for k, v in product_data.items() if k != "stock_distribution"}
            
            # Producto global (profile_id puede ser NULL en V2.0, pero mantenemos compatibilidad)
            product = Product(
                profile_id=profile.id,  # Temporal por compatibilidad
                **product_fields,
                moneda="HNL",
                activo=True
            )
            db.add(product)
            db.flush()
            products.append(product)
            
            print(f"  ✓ {product.nombre}")
        
        # ========== 5. CREAR STOCK POR UBICACIÓN ==========
        print("\n[5/5] Distribuyendo stock por ubicación...")
        for i, product in enumerate(products):
            stock_dist = stock_distributions[i]
            total_stock = 0
            
            for j, location in enumerate(locations):
                stock_qty = stock_dist[j]
                stock = Stock(
                    product_id=product.id,
                    location_id=location.id,  # ✅ V2.0: Stock asignado a ubicación
                    cantidad_disponible=stock_qty
                )
                db.add(stock)
                total_stock += stock_qty
                print(f"    • {location.nombre}: {stock_qty} unidades")
            
            print(f"    Total: {total_stock} unidades\n")
        
        db.commit()
        
        # ========== RESUMEN ==========
        print("="*70)
        print("✅ BASE DE DATOS V2.0 INICIALIZADA EXITOSAMENTE")
        print("="*70)
        print(f"\n📍 Ubicaciones creadas: {len(locations)}")
        for loc in locations:
            print(f"   - {loc.nombre} ({loc.tipo})")
        
        print(f"\n🤖 Perfiles de venta creados: {len(sales_profiles)}")
        for sp in sales_profiles:
            print(f"   - {sp.name} ({sp.tipo})")
        
        print(f"\n📦 Productos globales: {len(products)}")
        print(f"   - Celulares: 2")
        print(f"   - Accesorios: 2")
        
        print("\n🔗 API Endpoints disponibles:")
        print("   - http://localhost:8000/docs (Swagger UI)")
        print("   - GET /api/locations (Ver ubicaciones)")
        print("   - GET /api/sales-profiles (Ver perfiles de venta)")
        print("   - GET /api/products (Ver productos con stock total)")
        print("   - POST /api/orders (Crear orden especificando ubicación origen)")
        
        print("\n📝 Ejemplo de orden V2.0:")
        print("   POST /api/orders")
        print("   {")
        print('     "sales_profile_slug": "bot-whatsapp-1",')
        print(f'     "source_location_id": {locations[0].id},  # Tienda Centro')
        print('     "customer_name": "Juan Pérez",')
        print('     "customer_phone": "+504 9999-1234",')
        print('     "canal": "whatsapp",')
        print('     "metodo_pago": "efectivo",')
        print('     "items": [{"product_id": 1, "cantidad": 1}]')
        print("   }")
        print("="*70 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error al insertar datos: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
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
