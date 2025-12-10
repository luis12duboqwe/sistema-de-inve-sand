#!/usr/bin/env python3
"""Script rápido para diagnosticar y crear stock"""
import sys
sys.path.insert(0, '/workspaces/spark-template/backend')

from app.database import SessionLocal
from app.models import Product, Location, Stock

db = SessionLocal()

print("=" * 60)
print("📊 DIAGNÓSTICO DEL SISTEMA")
print("=" * 60)

# 1. Productos
products = db.query(Product).all()
print(f"\n📦 PRODUCTOS ({len(products)}):")
for p in products[:5]:
    stock_val = getattr(p, 'stock', 0) or getattr(p, 'stock_disponible', 0)
    print(f"  - ID {p.id}: {p.nombre} (Stock: {stock_val})")

# 2. Ubicaciones
locations = db.query(Location).all()
print(f"\n📍 UBICACIONES ({len(locations)}):")
for loc in locations:
    print(f"  - ID {loc.id}: {loc.nombre} ({loc.tipo})")

# 3. Stock (registros V2.0)
stocks = db.query(Stock).all()
print(f"\n📊 STOCK V2.0 ({len(stocks)} registros):")
if stocks:
    for s in stocks[:10]:
        prod = db.query(Product).get(s.product_id)
        loc = db.query(Location).get(s.location_id)
        print(f"  - {prod.nombre[:30]} @ {loc.nombre}: {s.cantidad_disponible}")
else:
    print("  ⚠️  NO HAY REGISTROS DE STOCK V2.0")
    print("\n🔧 CREANDO STOCK AHORA...")
    
    for product in products:
        for location in locations:
            # Asignar 1 unidad por defecto a cada ubicación
            cantidad = 1
            stock_entry = Stock(
                product_id=product.id,
                location_id=location.id,
                cantidad_disponible=cantidad,
                cantidad_reservada=0,
                cantidad_en_transito=0
            )
            db.add(stock_entry)
            print(f"    ✅ {product.nombre[:30]} → {location.nombre}: {cantidad}")
    
    db.commit()
    print("\n✅ STOCK CREADO EXITOSAMENTE")

db.close()
print("\n" + "=" * 60)
