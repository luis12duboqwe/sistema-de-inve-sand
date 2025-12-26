import sys
import os

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.database import SessionLocal
from app.models import Role, Permission, role_permissions

def fix_role_permissions():
    db = SessionLocal()
    try:
        print("🔄 Fixing role permissions...")
        
        # 1. Get Permissions Map
        permissions = db.query(Permission).all()
        permissions_map = {p.slug: p for p in permissions}
        
        if not permissions_map:
            print("❌ No permissions found! Run migrate_add_rbac.py first.")
            return

        # 2. Define Permissions for Roles
        ROLE_PERMISSIONS = {
            "Gerente": [
                "inventory:view", "inventory:create", "inventory:edit", "inventory:delete", "inventory:adjust",
                "orders:view", "orders:create", "orders:edit", "orders:delete",
                "locations:view", "locations:manage",
                "reports:view"
            ],
            "Vendedor": [
                "inventory:view",
                "orders:view", "orders:create", "orders:edit",
                "locations:view"
            ],
            "Invitado": [
                "inventory:view"
            ]
        }

        # 3. Update Roles
        for role_name, perm_slugs in ROLE_PERMISSIONS.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                print(f"  🛠️ Updating permissions for {role_name}...")
                new_perms = []
                for slug in perm_slugs:
                    if slug in permissions_map:
                        new_perms.append(permissions_map[slug])
                    else:
                        print(f"    ⚠️ Warning: Permission {slug} not found")
                
                role.permissions = new_perms
                print(f"    ✅ Assigned {len(new_perms)} permissions.")
            else:
                print(f"  ⚠️ Role {role_name} not found.")
        
        db.commit()
        print("✨ Permissions update complete.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_role_permissions()
