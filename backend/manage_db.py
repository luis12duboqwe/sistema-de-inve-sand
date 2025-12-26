import os
import subprocess
import sys

try:
    import sqlalchemy
except ImportError:
    print("❌ Error: SQLAlchemy no está instalado.")
    print("Por favor, activa el entorno virtual antes de ejecutar este script:")
    print("  source venv/bin/activate  (Linux/Mac)")
    print("  venv\\Scripts\\activate    (Windows)")
    sys.exit(1)

# Orden sugerido basado en dependencias lógicas
# (Core V2 -> Features -> Fixes)
MIGRATION_ORDER = [
    "migrate_to_locations_model.py",
    "migrate_add_rbac.py",
    "migrate_add_ai_intelligence.py",
    "migrate_add_financing.py",
    "migrate_add_returns.py",
    "migrate_add_trade_in.py",
    "migrate_add_tradein_details.py",
    "migrate_add_details_to_trade_in.py",
    "migrate_add_trade_in_policies.py",
    "migrate_add_imei_history.py",
    "migrate_add_transfer_id_to_imei.py",
    "migrate_add_reserved_stock.py",
    "migrate_add_is_serialized.py",
    "migrate_add_color.py",
    "migrate_add_normal_card_rate.py",
    "migrate_add_settings_to_profile.py",
    "migrate_add_admin_phone.py",
    "migrate_v2_fixes.py"
]

def run_migrations():
    print("=== Database Migration Manager ===")
    print("Este script ejecuta las migraciones en el orden recomendado.")
    
    files = [f for f in os.listdir('.') if f.startswith('migrate_') and f.endswith('.py')]
    
    # Sort by defined order, then alphabetical for unknown ones
    def sort_key(f):
        try:
            return MIGRATION_ORDER.index(f)
        except ValueError:
            return 999 + (1 if f > "" else 0) # Keep unknown at end

    files.sort(key=sort_key)

    print(f"Se encontraron {len(files)} scripts de migración.")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")

    print("\nOpciones:")
    print("a) Ejecutar TODAS (en orden)")
    print("q) Salir")
    
    choice = input("\nSeleccione una opción: ")
    
    if choice.lower() == 'a':
        for f in files:
            print(f"\n--------------------------------------------------")
            print(f"🚀 Ejecutando {f}...")
            try:
                subprocess.check_call([sys.executable, f])
                print(f"✅ {f} completado exitosamente.")
            except subprocess.CalledProcessError:
                print(f"❌ {f} falló. Deteniendo proceso.")
                print("Corrija el error antes de continuar.")
                break
    else:
        print("Saliendo.")

if __name__ == "__main__":
    run_migrations()
