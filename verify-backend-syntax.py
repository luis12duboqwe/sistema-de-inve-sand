#!/usr/bin/env python3
"""
Script para verificar que el backend puede importarse sin errores de sintaxis.
"""
import sys
import os

# Agregar backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("🔍 Verificando imports del backend...")

try:
    print("  ✓ Importando config...")
    from app import config
    
    print("  ✓ Importando database...")
    from app import database
    
    print("  ✓ Importando models...")
    from app import models
    
    print("  ✓ Importando schemas...")
    from app import schemas
    
    print("  ✓ Importando auth...")
    from app import auth
    
    print("  ✓ Importando routers...")
    from app.routers import (
        profiles, products, orders, faq, customers, reports,
        auth_router, stock_transfers, suppliers, stock_history,
        locations, sales_profiles
    )
    
    print("  ✓ Importando main...")
    from app import main
    
    print("\n✅ Todos los imports del backend son correctos")
    print("✅ No se encontraron errores de sintaxis Python")
    sys.exit(0)
    
except SyntaxError as e:
    print(f"\n❌ Error de sintaxis: {e}")
    print(f"   Archivo: {e.filename}")
    print(f"   Línea: {e.lineno}")
    sys.exit(1)
    
except ImportError as e:
    print(f"\n❌ Error de importación: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
