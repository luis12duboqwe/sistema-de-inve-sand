#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspaces/spark-template/backend')

from app.database import SessionLocal
from app.models import Product, Stock, Profile

db = SessionLocal()

print('=== PERFILES ===')
profiles = db.query(Profile).all()
for p in profiles:
    print(f'ID: {p.id}, Nombre: {p.name}, Slug: {p.slug}')

print('\n=== PRODUCTOS ===')
products = db.query(Product).all()
print(f'Total de productos: {len(products)}')
for p in products:
    stock = db.query(Stock).filter(Stock.product_id == p.id).first()
    stock_qty = stock.cantidad_disponible if stock else 0
    print(f'ID: {p.id}, SKU: {p.sku}, Nombre: {p.nombre}, Stock: {stock_qty}, Activo: {p.activo}')

db.close()
