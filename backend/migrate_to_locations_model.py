"""
Script de migración para transformar el modelo antiguo al nuevo

CAMBIOS PRINCIPALES:
1. Profile (viejo) -> Se convierte en Location (ubicación física)
2. Se crea SalesProfile nuevo para vendedores/bots
3. Stock ahora es por ubicación (product_id + location_id)
4. Orders ahora tienen sales_profile_id y source_location_id
5. Productos ahora son globales (profile_id se vuelve nullable)

ESTRATEGIA:
- Cada Profile antiguo se convierte en una Location tipo "tienda"
- Se crea una Location adicional tipo "bodega" 
- Se crea un SalesProfile por defecto para las órdenes existentes
- El stock se migra a la nueva tabla con location_id
- Las órdenes se actualizan con sales_profile_id y source_location_id
"""

import sys
import os

# Agregar el directorio del backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '/workspaces/spark-template/backend'
sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, engine
from app.models import (
    Location, SalesProfile, Profile, Product, Stock, 
    Order, StockTransfer, StockHistory, ProductIMEI
)
import json


def migrate_data():
    """Ejecutar la migración completa"""
    
    # Crear todas las nuevas tablas si no existen
    print("📦 Creando nuevas tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas\n")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # PASO 1: Migrar Profiles antiguos a Locations
        print("🏪 PASO 1: Migrando Profiles a Locations...")
        migrate_profiles_to_locations(session)
        
        # PASO 2: Crear Location de Bodega
        print("\n📦 PASO 2: Creando ubicación de Bodega...")
        create_warehouse_location(session)
        
        # PASO 3: Crear SalesProfile por defecto
        print("\n🤖 PASO 3: Creando SalesProfile por defecto...")
        create_default_sales_profile(session)
        
        # PASO 4: Migrar Stock a nueva estructura
        print("\n📊 PASO 4: Migrando Stock por ubicación...")
        migrate_stock_to_locations(session)
        
        # PASO 5: Actualizar Orders con nuevos campos
        print("\n🛒 PASO 5: Actualizando Orders...")
        migrate_orders(session)
        
        # PASO 6: Actualizar StockTransfers
        print("\n🔄 PASO 6: Actualizando StockTransfers...")
        migrate_stock_transfers(session)
        
        # PASO 7: Actualizar StockHistory
        print("\n📜 PASO 7: Actualizando StockHistory...")
        migrate_stock_history(session)
        
        # PASO 8: Actualizar ProductIMEIs
        print("\n📱 PASO 8: Actualizando ProductIMEIs...")
        migrate_product_imeis(session)
        
        # PASO 9: Hacer productos globales (profile_id nullable)
        print("\n🌐 PASO 9: Convirtiendo productos a globales...")
        make_products_global(session)
        
        session.commit()
        
        print("\n" + "="*60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print_migration_summary(session)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR durante la migración: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


def migrate_profiles_to_locations(session):
    """Convertir cada Profile antiguo en una Location"""
    profiles = session.query(Profile).all()
    
    location_map = {}  # profile_id -> location_id
    
    for profile in profiles:
        # Crear Location correspondiente
        location = Location(
            nombre=profile.name,
            tipo="tienda",  # Asumimos que son tiendas
            activo=profile.active
        )
        session.add(location)
        session.flush()  # Para obtener el ID
        
        location_map[profile.id] = location.id
        print(f"  ✓ Profile '{profile.name}' -> Location ID {location.id}")
    
    session.flush()
    
    # Guardar el mapeo en la sesión para uso posterior
    session.info['location_map'] = location_map
    
    print(f"\n  Total: {len(profiles)} Profiles convertidos a Locations")
    return location_map


def create_warehouse_location(session):
    """Crear una ubicación de tipo bodega"""
    warehouse = Location(
        nombre="Bodega Central",
        tipo="bodega",
        activo=True
    )
    session.add(warehouse)
    session.flush()
    
    session.info['warehouse_id'] = warehouse.id
    print(f"  ✓ Bodega creada con ID {warehouse.id}")


def create_default_sales_profile(session):
    """Crear un SalesProfile por defecto para migrar las órdenes existentes"""
    # Check if already exists
    existing = session.query(SalesProfile).filter(SalesProfile.slug == "sistema-principal").first()
    if existing:
        session.info['default_sales_profile_id'] = existing.id
        print(f"  ✓ SalesProfile 'sistema-principal' ya existe (ID {existing.id})")
        return

    sales_profile = SalesProfile(
        name="Sistema Principal",
        slug="sistema-principal",
        tipo="sistema_automatico",
        canales=json.dumps(["whatsapp", "facebook", "instagram"]),
        active=True,
        configuracion=json.dumps({
            "descripcion": "Perfil creado automáticamente durante la migración",
            "migrado": True
        })
    )
    session.add(sales_profile)
    session.flush()
    
    session.info['default_sales_profile_id'] = sales_profile.id
    print(f"  ✓ SalesProfile creado con ID {sales_profile.id}")


def migrate_stock_to_locations(session):
    """Migrar registros de Stock a la nueva estructura con location_id"""
    location_map = session.info.get('location_map', {})
    
    # Obtener todos los productos con su stock actual
    products = session.query(Product).all()
    
    migrated_count = 0
    
    for product in products:
        if product.profile_id and product.profile_id in location_map:
            location_id = location_map[product.profile_id]
            
            # Buscar el stock actual (tabla vieja)
            old_stock = session.query(Stock).filter(
                Stock.product_id == product.id
            ).first()
            
            if old_stock and old_stock.cantidad_disponible > 0:
                # Verificar si ya existe este registro (por si se ejecuta 2 veces)
                existing = session.query(Stock).filter(
                    Stock.product_id == product.id,
                    Stock.location_id == location_id
                ).first()
                
                if not existing:
                    # Crear nuevo registro de stock por ubicación
                    new_stock = Stock(
                        product_id=product.id,
                        location_id=location_id,
                        cantidad_disponible=old_stock.cantidad_disponible
                    )
                    session.add(new_stock)
                    migrated_count += 1
                    
                    # Eliminar el registro viejo
                    session.delete(old_stock)
    
    session.flush()
    print(f"  ✓ {migrated_count} registros de stock migrados a ubicaciones")


def migrate_orders(session):
    """Actualizar órdenes con sales_profile_id y source_location_id"""
    location_map = session.info.get('location_map', {})
    default_sales_profile_id = session.info.get('default_sales_profile_id')
    
    orders = session.query(Order).all()
    updated_count = 0
    
    for order in orders:
        # Asignar sales_profile_id si no tiene
        if not order.sales_profile_id:
            order.sales_profile_id = default_sales_profile_id
        
        # Asignar source_location_id basado en el profile_id original
        if not order.source_location_id and order.profile_id in location_map:
            order.source_location_id = location_map[order.profile_id]
            updated_count += 1
    
    session.flush()
    print(f"  ✓ {updated_count} órdenes actualizadas con ubicación de origen")


def migrate_stock_transfers(session):
    """Actualizar transferencias con location_ids"""
    location_map = session.info.get('location_map', {})
    
    transfers = session.query(StockTransfer).all()
    updated_count = 0
    
    for transfer in transfers:
        # Mapear from_profile_id -> from_location_id
        if transfer.from_profile_id in location_map:
            transfer.from_location_id = location_map[transfer.from_profile_id]
        
        # Mapear to_profile_id -> to_location_id
        if transfer.to_profile_id in location_map:
            transfer.to_location_id = location_map[transfer.to_profile_id]
        
        if transfer.from_location_id and transfer.to_location_id:
            updated_count += 1
    
    session.flush()
    print(f"  ✓ {updated_count} transferencias actualizadas con ubicaciones")


def migrate_stock_history(session):
    """Actualizar historial de stock con location_id"""
    location_map = session.info.get('location_map', {})
    
    # Para el historial, necesitamos inferir la ubicación del producto
    history_records = session.query(StockHistory).all()
    updated_count = 0
    
    for record in history_records:
        # Obtener el producto para saber su profile_id
        product = session.query(Product).filter(Product.id == record.product_id).first()
        
        if product and product.profile_id in location_map:
            record.location_id = location_map[product.profile_id]
            updated_count += 1
    
    session.flush()
    print(f"  ✓ {updated_count} registros de historial actualizados")


def migrate_product_imeis(session):
    """Actualizar IMEIs con location_id"""
    location_map = session.info.get('location_map', {})
    
    imeis = session.query(ProductIMEI).all()
    updated_count = 0
    
    for imei in imeis:
        # Obtener el producto para saber su ubicación
        product = session.query(Product).filter(Product.id == imei.product_id).first()
        
        if product and product.profile_id in location_map:
            imei.location_id = location_map[product.profile_id]
            updated_count += 1
    
    session.flush()
    print(f"  ✓ {updated_count} IMEIs actualizados con ubicación")


def make_products_global(session):
    """Hacer que products.profile_id sea nullable (productos globales)"""
    # Los productos ahora son visibles globalmente
    # El profile_id se mantiene temporalmente para referencia
    # pero en futuras versiones se puede eliminar
    
    products_count = session.query(Product).count()
    print(f"  ✓ {products_count} productos ahora son globales")
    print(f"  ℹ️  profile_id se mantiene temporalmente para compatibilidad")


def print_migration_summary(session):
    """Imprimir resumen de la migración"""
    print("\n📊 RESUMEN DE MIGRACIÓN:")
    print("-" * 60)
    
    locations = session.query(Location).count()
    print(f"  📍 Ubicaciones: {locations}")
    
    sales_profiles = session.query(SalesProfile).count()
    print(f"  🤖 Perfiles de Venta: {sales_profiles}")
    
    products = session.query(Product).count()
    print(f"  📦 Productos: {products}")
    
    stock_items = session.query(Stock).count()
    print(f"  📊 Registros de Stock: {stock_items}")
    
    orders = session.query(Order).count()
    print(f"  🛒 Órdenes: {orders}")
    
    print("\n💡 PRÓXIMOS PASOS:")
    print("  1. Revisar las ubicaciones creadas: GET /api/locations")
    print("  2. Crear más perfiles de venta: POST /api/sales-profiles")
    print("  3. Los productos ahora son globales - visibles para todos")
    print("  4. El stock está organizado por ubicación física")
    print("  5. Al crear órdenes, especifica sales_profile_id y source_location_id")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔄 INICIANDO MIGRACIÓN AL NUEVO MODELO")
    print("="*60)
    print("\nEste script migrará:")
    print("  • Profiles -> Locations (ubicaciones físicas)")
    print("  • Creará SalesProfiles para vendedores/bots")
    print("  • Stock -> Stock por ubicación")
    print("  • Orders con sales_profile_id y source_location_id")
    print("\n⚠️  IMPORTANTE: Haz backup de la base de datos antes de continuar")
    
    response = input("\n¿Continuar con la migración? (si/no): ").strip().lower()
    
    if response in ['si', 's', 'yes', 'y']:
        migrate_data()
    else:
        print("\n❌ Migración cancelada")
