#!/usr/bin/env python3
"""
Script para crear registros de Stock vinculando productos con ubicaciones.
Esto es necesario para el sistema V2.0 de multi-ubicaciones.
"""

from app.database import SessionLocal
from app.models import Product, Location, Stock
from datetime import datetime

def create_stock_records():
    db = SessionLocal()
    
    try:
        # Obtener productos y ubicaciones
        products = db.query(Product).all()
        locations = db.query(Location).all()
        
        print(f'📦 Productos encontrados: {len(products)}')
        print(f'📍 Ubicaciones encontradas: {len(locations)}')
        
        # Verificar stock existente
        existing_stock = db.query(Stock).count()
        print(f'📊 Registros de stock existentes: {existing_stock}')
        
        if existing_stock == 0 and products and locations:
            print('\n🔧 Creando registros de stock para productos en ubicaciones...')
            
            for product in products:
                for location in locations:
                    # Crear stock inicial (distribuir stock entre ubicaciones)
                    cantidad = product.stock // len(locations) if product.stock > 0 else 0
                    
                    stock_entry = Stock(
                        product_id=product.id,
                        location_id=location.id,
                        cantidad_disponible=cantidad,
                        cantidad_reservada=0,
                        cantidad_en_transito=0
                    )
                    db.add(stock_entry)
                    print(f'  ✅ {product.nombre[:40]:<40} → {location.nombre:20} : {cantidad} unidades')
            
            db.commit()
            print('\n✅ Stock creado exitosamente')
        elif existing_stock > 0:
            print('\nℹ️  Stock ya existe. Mostrando registros actuales:')
            stocks = db.query(Stock).join(Product).join(Location).all()
            for stock in stocks:
                print(f'  📍 {stock.product.nombre[:40]:<40} @ {stock.location.nombre:20} : {stock.cantidad_disponible}')
        else:
            print('\n⚠️  No hay productos o ubicaciones para crear stock')
            
    except Exception as e:
        print(f'\n❌ Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    create_stock_records()
