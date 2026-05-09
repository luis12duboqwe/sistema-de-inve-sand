import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.config import settings
from app.models import Role, Permission, User, role_permissions
from passlib.context import CryptContext

# Configurar contexto de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def migrate():
    print("🔄 Iniciando migración RBAC (Roles y Permisos)...")
    
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. Crear tablas nuevas
        print("📊 Creando tablas de roles y permisos...")
        Base.metadata.create_all(bind=engine)

        # 1.5 Agregar columna role_id a users si no existe
        print("🛠️ Verificando esquema de usuarios...")
        with engine.connect() as conn:
            # Verificar columnas existentes
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()] # row[1] es el nombre de la columna
            
            if "role_id" not in columns:
                print("  ➕ Agregando columna role_id a tabla users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL"))
                conn.commit()
            else:
                print("  ✅ Columna role_id ya existe.")
        
        # 2. Definir Permisos del Sistema
        SYSTEM_PERMISSIONS = [
            # Inventario
            {"slug": "inventory:view", "description": "Ver inventario y stock", "module": "inventory"},
            {"slug": "inventory:create", "description": "Crear productos", "module": "inventory"},
            {"slug": "inventory:edit", "description": "Editar productos", "module": "inventory"},
            {"slug": "inventory:delete", "description": "Eliminar productos", "module": "inventory"},
            {"slug": "inventory:adjust", "description": "Ajustar stock manualmente", "module": "inventory"},
            {"slug": "inventory:count", "description": "Realizar conteos físicos", "module": "inventory"},
            {"slug": "purchases:manage", "description": "Registrar recepciones de compras", "module": "purchases"},
            {"slug": "cash_closes:manage", "description": "Cerrar caja por tienda", "module": "cash_closes"},
            {"slug": "audit:view", "description": "Ver bitácora de auditoría", "module": "audit"},
            
            # Órdenes
            {"slug": "orders:view", "description": "Ver órdenes", "module": "orders"},
            {"slug": "orders:create", "description": "Crear órdenes", "module": "orders"},
            {"slug": "orders:edit", "description": "Editar órdenes", "module": "orders"},
            {"slug": "orders:delete", "description": "Eliminar/Cancelar órdenes", "module": "orders"},
            
            # Ubicaciones (Tiendas)
            {"slug": "locations:view", "description": "Ver ubicaciones", "module": "locations"},
            {"slug": "locations:manage", "description": "Crear/Editar/Borrar ubicaciones", "module": "locations"},
            {"slug": "locations:access_manage", "description": "Gestionar accesos por ubicación", "module": "locations"},
            
            # Configuración y Usuarios
            {"slug": "settings:view", "description": "Ver configuraciones", "module": "settings"},
            {"slug": "settings:edit", "description": "Editar configuraciones críticas (Bots, API)", "module": "settings"},
            {"slug": "users:manage", "description": "Gestionar usuarios y roles", "module": "users"},
            
            # Reportes
            {"slug": "reports:view", "description": "Ver reportes financieros", "module": "reports"},

            # Solicitudes de fotos
            {"slug": "photo_requests:list", "description": "Listar solicitudes de fotos", "module": "photo_requests"},
            {"slug": "photo_requests:read", "description": "Ver solicitudes de fotos", "module": "photo_requests"},
            {"slug": "photo_requests:update", "description": "Actualizar solicitudes de fotos", "module": "photo_requests"},
            {"slug": "photo_requests:upload", "description": "Cargar fotos solicitadas", "module": "photo_requests"},
            {"slug": "photo_requests:send", "description": "Enviar fotos al cliente", "module": "photo_requests"},
        ]

        print("🔑 Creando permisos...")
        permissions_map = {}
        for p_data in SYSTEM_PERMISSIONS:
            perm = db.query(Permission).filter(Permission.slug == p_data["slug"]).first()
            if not perm:
                perm = Permission(**p_data)
                db.add(perm)
                db.flush()
            permissions_map[p_data["slug"]] = perm

        # 3. Definir Roles por Defecto
        ROLES_CONFIG = [
            {
                "name": "Super Admin",
                "description": "Acceso total al sistema",
                "is_system_role": True,
                "permissions": list(permissions_map.values()) # Todos
            },
            {
                "name": "Gerente",
                "description": "Gestión de inventario y ventas. Sin acceso a configuración crítica.",
                "is_system_role": False,
                "permissions": [
                    permissions_map["inventory:view"],
                    permissions_map["inventory:create"],
                    permissions_map["inventory:edit"],
                    permissions_map["inventory:delete"], # Puede borrar productos? Asumimos que sí
                    permissions_map["inventory:adjust"],
                    permissions_map["inventory:count"],
                    permissions_map["purchases:manage"],
                    permissions_map["cash_closes:manage"],
                    permissions_map["audit:view"],
                    permissions_map["orders:view"],
                    permissions_map["orders:create"],
                    permissions_map["orders:edit"],
                    permissions_map["orders:delete"],
                    permissions_map["locations:view"], # Solo ver
                    permissions_map["locations:manage"],
                    permissions_map["reports:view"],
                    permissions_map["photo_requests:list"],
                    permissions_map["photo_requests:read"],
                    permissions_map["photo_requests:update"],
                    permissions_map["photo_requests:upload"],
                    permissions_map["photo_requests:send"],
                ]
            },
            {
                "name": "Vendedor",
                "description": "Solo ventas y consulta de stock.",
                "is_system_role": False,
                "permissions": [
                    permissions_map["inventory:view"],
                    permissions_map["inventory:count"],
                    permissions_map["orders:view"],
                    permissions_map["orders:create"],
                    permissions_map["locations:view"],
                    permissions_map["photo_requests:list"],
                    permissions_map["photo_requests:read"],
                    permissions_map["photo_requests:update"],
                    permissions_map["photo_requests:upload"],
                    permissions_map["photo_requests:send"],
                ]
            },
            {
                "name": "Invitado",
                "description": "Vista de catálogo solamente.",
                "is_system_role": False,
                "permissions": [
                    permissions_map["inventory:view"], # Limitado en frontend
                ]
            }
        ]

        print("busts Creando roles...")
        for r_data in ROLES_CONFIG:
            role = db.query(Role).filter(Role.name == r_data["name"]).first()
            if not role:
                role = Role(
                    name=r_data["name"],
                    description=r_data["description"],
                    is_system_role=r_data["is_system_role"]
                )
                db.add(role)
                db.flush()
                # Asignar permisos
                role.permissions = r_data["permissions"]
            else:
                # Actualizar permisos si ya existe (reset a default)
                role.permissions = r_data["permissions"]

        # 4. Crear Usuario Admin por defecto si no existe
        print("👤 Verificando usuario administrador...")
        admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if not admin_user:
            print("✨ Creando usuario 'admin' por defecto...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                full_name="Administrador del Sistema",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
                role_id=admin_role.id
            )
            db.add(admin_user)
        else:
            # Asegurar que tenga el rol
            if not admin_user.role_id:
                admin_user.role_id = admin_role.id
                db.add(admin_user)
            print("ℹ️ Usuario 'admin' ya existe.")

        db.commit()
        print("✅ Migración RBAC completada exitosamente.")

    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
