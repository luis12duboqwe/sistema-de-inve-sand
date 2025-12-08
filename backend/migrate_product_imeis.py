"""
Migración: Agregar tabla ProductIMEI para múltiples IMEIs por producto

Esta migración crea la tabla product_imeis para permitir registrar
múltiples IMEIs para productos con stock > 1.
"""

from sqlalchemy import create_engine, text
from app.config import settings
from app.database import Base
from app.models import Product, ProductIMEI
import sys

def run_migration():
    """Ejecuta la migración de la base de datos"""
    engine = create_engine(settings.database_url)
    
    print("🔄 Iniciando migración de ProductIMEI...")
    
    try:
        # Crear la tabla product_imeis
        print("📋 Creando tabla product_imeis...")
        ProductIMEI.__table__.create(engine, checkfirst=True)
        print("✅ Tabla product_imeis creada exitosamente")
        
        # Verificar si la columna imei existe antes de intentar migrar
        print("🔍 Verificando existencia de columna 'imei' antigua...")
        with engine.connect() as conn:
            try:
                # Intentar leer la columna imei
                result = conn.execute(text("SELECT imei FROM products LIMIT 1"))
                has_imei_column = True
                print("  ✓ Columna 'imei' encontrada")
            except Exception:
                has_imei_column = False
                print("  ℹ️  Columna 'imei' no existe (base de datos nueva)")
            
            # Solo migrar si existe la columna antigua
            if has_imei_column:
                print("🔄 Migrando IMEIs existentes...")
                result = conn.execute(text("""
                    SELECT id, imei 
                    FROM products 
                    WHERE imei IS NOT NULL AND imei != ''
                """))
                
                products_with_imei = result.fetchall()
                
                if products_with_imei:
                    print(f"📱 Encontrados {len(products_with_imei)} productos con IMEI")
                    
                    for product_id, imei in products_with_imei:
                        # Insertar en product_imeis
                        conn.execute(text("""
                            INSERT INTO product_imeis (product_id, imei, vendido, created_at)
                            VALUES (:product_id, :imei, false, CURRENT_TIMESTAMP)
                        """), {"product_id": product_id, "imei": imei})
                        print(f"  ✓ Migrado IMEI {imei} del producto {product_id}")
                    
                    conn.commit()
                    print(f"✅ {len(products_with_imei)} IMEIs migrados exitosamente")
                else:
                    print("ℹ️  No hay productos con IMEI para migrar")
        
        print("\n✅ ¡Migración completada exitosamente!")
        print("\n📝 Notas:")
        print("  - Tabla 'product_imeis' lista para almacenar múltiples IMEIs por producto")
        print("  - Cada producto puede tener N IMEIs según su cantidad en stock")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
