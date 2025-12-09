#!/usr/bin/env python3
"""
Script simplificado de migración
"""
import sys
sys.path.insert(0, '/workspaces/spark-template/backend')

from sqlalchemy.orm import sessionmaker
from app.database import Base, engine
from app.models import Location, SalesProfile, Profile
import json

print("\n" + "="*60)
print("🔄 MIGRACIÓN RÁPIDA AL NUEVO MODELO")
print("="*60 + "\n")

# Crear tablas
print("1️⃣  Creando nuevas tablas...")
Base.metadata.create_all(bind=engine)
print("   ✅ Tablas creadas\n")

# Verificar datos existentes
Session = sessionmaker(bind=engine)
session = Session()

profiles = session.query(Profile).all()
locations = session.query(Location).all()
sales_profiles = session.query(SalesProfile).all()

print(f"2️⃣  Estado actual:")
print(f"   📊 Profiles antiguos: {len(profiles)}")
print(f"   📍 Locations: {len(locations)}")
print(f"   🤖 Sales Profiles: {len(sales_profiles)}\n")

# Si no hay ubicaciones, crear desde profiles
if len(locations) == 0 and len(profiles) > 0:
    print("3️⃣  Migrando Profiles → Locations...")
    for profile in profiles:
        location = Location(
            nombre=profile.name,
            tipo="tienda",
            activo=profile.active
        )
        session.add(location)
        print(f"   ✓ '{profile.name}' → Location")
    
    # Crear bodega
    bodega = Location(
        nombre="Bodega Central",
        tipo="bodega",
        activo=True
    )
    session.add(bodega)
    print(f"   ✓ 'Bodega Central' creada\n")
    
    session.commit()
else:
    print("3️⃣  ✅ Ubicaciones ya existen\n")

# Si no hay sales profiles, crear uno por defecto
if len(sales_profiles) == 0:
    print("4️⃣  Creando SalesProfile por defecto...")
    sp = SalesProfile(
        name="Sistema Principal",
        slug="sistema-principal",
        tipo="sistema_automatico",
        canales=json.dumps(["whatsapp", "facebook", "instagram"]),
        active=True
    )
    session.add(sp)
    session.commit()
    print("   ✅ SalesProfile creado\n")
else:
    print("4️⃣  ✅ Sales Profiles ya existen\n")

# Resumen final
locations = session.query(Location).all()
sales_profiles = session.query(SalesProfile).all()

print("="*60)
print("✅ MIGRACIÓN COMPLETADA")
print("="*60)
print(f"\n📊 Resultado:")
print(f"   📍 Ubicaciones: {len(locations)}")
for loc in locations:
    print(f"      - {loc.nombre} ({loc.tipo})")
print(f"\n   🤖 Perfiles de Venta: {len(sales_profiles)}")
for sp in sales_profiles:
    print(f"      - {sp.name} ({sp.tipo})")

print(f"\n💡 Próximos pasos:")
print(f"   1. Crear más ubicaciones: POST /api/locations")
print(f"   2. Crear más sales profiles: POST /api/sales-profiles")
print(f"   3. Ver API docs: http://localhost:8000/docs")
print()

session.close()
