import sys
import os

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.database import SessionLocal
from app.models import Role, Permission

def ensure_roles():
    db = SessionLocal()
    try:
        print("🔄 Checking default roles...")
        
        # Define roles to ensure
        ROLES_TO_CREATE = [
            {
                "name": "Gerente",
                "description": "Gestión de inventario y ventas. Sin acceso a configuración crítica.",
                "is_system_role": False
            },
            {
                "name": "Vendedor",
                "description": "Solo puede crear órdenes y ver stock. No puede editar productos ni ver reportes financieros.",
                "is_system_role": False
            },
            {
                "name": "Invitado",
                "description": "Solo lectura de inventario.",
                "is_system_role": False
            }
        ]

        for role_data in ROLES_TO_CREATE:
            role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not role:
                print(f"  ➕ Creating role: {role_data['name']}")
                new_role = Role(**role_data)
                db.add(new_role)
            else:
                print(f"  ✅ Role exists: {role_data['name']}")
        
        db.commit()
        print("✨ Roles verification complete.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    ensure_roles()
