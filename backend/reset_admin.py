import sys
import os

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.database import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash

def reset_admin():
    db = SessionLocal()
    try:
        # 1. Get or Create Role
        print("Checking roles...")
        admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
        if not admin_role:
            print("Creating Super Admin role...")
            admin_role = Role(name="Super Admin", description="Full Access", is_system_role=True)
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        else:
            print(f"Found role: {admin_role.name} (ID: {admin_role.id})")

        # 2. Get or Create User
        print("Checking admin user...")
        user = db.query(User).filter(User.username == "admin").first()
        password = "admin123"
        hashed_pw = get_password_hash(password)

        if user:
            print("Updating existing admin user...")
            user.hashed_password = hashed_pw
            user.role_id = admin_role.id
            user.is_active = True
            user.is_superuser = True
        else:
            print("Creating new admin user...")
            user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hashed_pw,
                role_id=admin_role.id,
                is_active=True,
                is_superuser=True
            )
            db.add(user)

        db.commit()
        print("---------------------------------------------------")
        print(f"✅ Admin user configured successfully.")
        print(f"👤 Username: admin")
        print(f"🔑 Password: {password}")
        print("---------------------------------------------------")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin()
