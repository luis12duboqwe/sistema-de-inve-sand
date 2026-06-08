import math
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Permission, Role, User
from app.schemas import (
    PermissionResponse,
    RoleResponse,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
    PaginatedResponse,
)
from app.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
    check_permission,
)
from app.config import settings
from app.dependencies.rate_limiting import check_auth_rate_limit

router = APIRouter(prefix="/api/auth", tags=["authentication"])

SYSTEM_PERMISSIONS = [
    {"slug": "inventory:view", "description": "Ver inventario y stock", "module": "inventory"},
    {"slug": "inventory:create", "description": "Crear productos", "module": "inventory"},
    {"slug": "inventory:edit", "description": "Editar productos", "module": "inventory"},
    {"slug": "inventory:delete", "description": "Eliminar productos", "module": "inventory"},
    {"slug": "inventory:adjust", "description": "Ajustar stock manualmente", "module": "inventory"},
    {"slug": "inventory:count", "description": "Realizar conteos físicos", "module": "inventory"},
    {"slug": "purchases:manage", "description": "Registrar recepciones de compras", "module": "purchases"},
    {"slug": "cash_closes:manage", "description": "Cerrar caja por tienda", "module": "cash_closes"},
    {"slug": "audit:view", "description": "Ver bitácora de auditoría", "module": "audit"},
    {"slug": "orders:view", "description": "Ver órdenes", "module": "orders"},
    {"slug": "orders:create", "description": "Crear órdenes", "module": "orders"},
    {"slug": "orders:edit", "description": "Editar órdenes", "module": "orders"},
    {"slug": "orders:delete", "description": "Eliminar/Cancelar órdenes", "module": "orders"},
    {"slug": "locations:view", "description": "Ver ubicaciones", "module": "locations"},
    {"slug": "locations:manage", "description": "Crear/Editar/Borrar ubicaciones", "module": "locations"},
    {"slug": "locations:access_manage", "description": "Gestionar accesos por ubicación", "module": "locations"},
    {"slug": "settings:view", "description": "Ver configuraciones", "module": "settings"},
    {"slug": "settings:edit", "description": "Editar configuraciones críticas del sistema", "module": "settings"},
    {"slug": "ai:manage", "description": "Gestionar operaciones de IA (estado, entrenamiento y configuración)", "module": "ai"},
    {"slug": "users:manage", "description": "Gestionar usuarios y roles", "module": "users"},
    {"slug": "reports:view", "description": "Ver reportes financieros", "module": "reports"},
    {"slug": "photo_requests:list", "description": "Listar solicitudes de fotos", "module": "photo_requests"},
    {"slug": "photo_requests:read", "description": "Ver solicitudes de fotos", "module": "photo_requests"},
    {"slug": "photo_requests:update", "description": "Actualizar solicitudes de fotos", "module": "photo_requests"},
    {"slug": "photo_requests:upload", "description": "Cargar fotos solicitadas", "module": "photo_requests"},
    {"slug": "photo_requests:send", "description": "Enviar fotos al cliente", "module": "photo_requests"},
]

SYSTEM_ROLE_CONFIG = [
    {
        "name": "Super Admin",
        "description": "Acceso total al sistema",
        "is_system_role": True,
        "permission_slugs": [permission["slug"] for permission in SYSTEM_PERMISSIONS],
    },
    {
        "name": "Admin",
        "description": "Administración operativa del sistema",
        "is_system_role": True,
        "permission_slugs": [
            "inventory:view",
            "inventory:create",
            "inventory:edit",
            "inventory:delete",
            "inventory:adjust",
            "inventory:count",
            "purchases:manage",
            "cash_closes:manage",
            "audit:view",
            "orders:view",
            "orders:create",
            "orders:edit",
            "orders:delete",
            "locations:view",
            "locations:manage",
            "locations:access_manage",
            "settings:view",
            "settings:edit",
            "reports:view",
            "users:manage",
            "photo_requests:list",
            "photo_requests:read",
            "photo_requests:update",
            "photo_requests:upload",
            "photo_requests:send",
        ],
    },
    {
        "name": "Gerente",
        "description": "Gestión de inventario y ventas",
        "is_system_role": True,
        "permission_slugs": [
            "inventory:view",
            "inventory:create",
            "inventory:edit",
            "inventory:delete",
            "inventory:adjust",
            "inventory:count",
            "purchases:manage",
            "cash_closes:manage",
            "audit:view",
            "orders:view",
            "orders:create",
            "orders:edit",
            "orders:delete",
            "locations:view",
            "locations:manage",
            "settings:view",
            "reports:view",
            "photo_requests:list",
            "photo_requests:read",
            "photo_requests:update",
            "photo_requests:upload",
            "photo_requests:send",
        ],
    },
    {
        "name": "Vendedor",
        "description": "Solo ventas y consulta de stock",
        "is_system_role": True,
        "permission_slugs": [
            "inventory:view",
            "inventory:count",
            "orders:view",
            "orders:create",
            "locations:view",
            "photo_requests:list",
            "photo_requests:read",
            "photo_requests:update",
            "photo_requests:upload",
            "photo_requests:send",
        ],
    },
    {
        "name": "Invitado",
        "description": "Vista de catálogo solamente",
        "is_system_role": True,
        "permission_slugs": ["inventory:view"],
    },
]


def ensure_default_rbac(db: Session) -> None:
    permission_by_slug = {permission.slug: permission for permission in db.query(Permission).all()}

    permissions_changed = False
    for definition in SYSTEM_PERMISSIONS:
        if definition["slug"] not in permission_by_slug:
            permission = Permission(
                slug=definition["slug"],
                description=definition["description"],
                module=definition["module"],
            )
            db.add(permission)
            db.flush()
            permission_by_slug[permission.slug] = permission
            permissions_changed = True

    roles_changed = False
    for definition in SYSTEM_ROLE_CONFIG:
        role = db.query(Role).filter(Role.name == definition["name"]).first()
        role_permissions = [
            permission_by_slug[slug]
            for slug in definition["permission_slugs"]
            if slug in permission_by_slug
        ]

        if not role:
            role = Role(
                name=definition["name"],
                description=definition["description"],
                is_system_role=definition["is_system_role"],
            )
            role.permissions = role_permissions
            db.add(role)
            roles_changed = True
            continue

        existing_slugs = {permission.slug for permission in (role.permissions or [])}
        required_slugs = {permission.slug for permission in role_permissions}
        if not required_slugs.issubset(existing_slugs):
            role.permissions = role_permissions
            roles_changed = True

        if not role.is_system_role:
            role.is_system_role = definition["is_system_role"]
            roles_changed = True

    if permissions_changed or roles_changed:
        db.commit()


def ensure_superuser_has_role(db: Session, user: User) -> User:
    """Garantiza que un superusuario tenga rol 'Super Admin' asignado."""
    if not user.is_superuser:
        return user

    ensure_default_rbac(db)
    super_admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
    if not super_admin_role:
        return user

    if user.role_id == super_admin_role.id:
        return user

    user.role_id = super_admin_role.id
    db.commit()
    db.refresh(user)
    return user


def _is_super_admin_role(role: Optional[Role]) -> bool:
    return bool(role and role.name.strip().lower().replace(" ", "") == "superadmin")


def _require_superuser_for_super_admin_role(current_user: User, role: Optional[Role]) -> None:
    if _is_super_admin_role(role) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Super Admin puede crear o asignar el rol Super Admin"
        )


def _require_superuser_for_super_admin_target(current_user: User, target_user: User) -> None:
    if target_user.is_superuser and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Super Admin puede modificar cuentas Super Admin"
        )

@router.post("/setup", response_model=Token)
def setup_initial_admin(user: UserCreate, db: Session = Depends(get_db)):
    """
    Setup the first Super Admin user.
    Only works if no users exist in the database.
    """
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System already initialized. Use login."
        )
    
    # Ensure default RBAC exists before assigning the initial admin role
    ensure_default_rbac(db)

    # Create Super Admin
    hashed_password = get_password_hash(user.password)
    
    # Find Super Admin Role
    admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
    
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_superuser=True,
        is_active=True,
        role_id=admin_role.id if admin_role else None
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Login automatically
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": db_user}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("users:manage"))
):
    """
    Register a new user. Requires Superuser privileges.
    """
    # Check if username exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    normalized_email = user.email.strip() if user.email else None
    if normalized_email:
        db_user = db.query(User).filter(User.email == normalized_email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    selected_role = db.query(Role).filter(Role.id == user.role_id).first() if user.role_id else None
    if user.role_id and not selected_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role with ID {user.role_id} not found")
    _require_superuser_for_super_admin_role(current_user, selected_role)
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=normalized_email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role_id=user.role_id,
        is_superuser=_is_super_admin_role(selected_role),
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _rate_limit: dict = Depends(check_auth_rate_limit),
):
    """
    Login and get an access token.
    """
    ensure_default_rbac(db)
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = ensure_superuser_has_role(db, user)
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information.
    
    Returns:
        Current user information
    """
    return ensure_superuser_has_role(db, current_user)


@router.put("/me", response_model=UserResponse)
def update_user_me(
    updates: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information.
    
    Args:
        - updates: Fields to update
        
    Returns:
        Updated user information
    """
    if updates.email is not None:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(
            User.email == updates.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = updates.email
    
    if updates.full_name is not None:
        current_user.full_name = updates.full_name
    
    if updates.password is not None:
        current_user.hashed_password = get_password_hash(updates.password)
    
    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


from app.schemas import Token, UserCreate, UserResponse, UserUpdate, RoleResponse
from app.models import User, Role

# ... existing imports ...

@router.get("/roles", response_model=PaginatedResponse[RoleResponse])
def list_roles(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Resultados por página"),
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db)
):
    """Lista roles disponibles con paginación."""
    ensure_default_rbac(db)
    query = db.query(Role).order_by(Role.name.asc())
    total = query.count()
    offset = (page - 1) * per_page
    roles = query.offset(offset).limit(per_page).all()
    pages = math.ceil(total / per_page) if total else 0

    return PaginatedResponse(
        items=roles,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    role_id: int = Query(..., description="ID of the new role"),
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db)
):
    """
    Update a user's role (superuser only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    _require_superuser_for_super_admin_target(current_user, user)
    _require_superuser_for_super_admin_role(current_user, role)

    user.role_id = role_id
    user.is_superuser = _is_super_admin_role(role)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_admin(
    user_id: int,
    updates: UserUpdate,
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db)
):
    """
    Update any user information (superuser only).
    Can update role, active status, password, etc.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    _require_superuser_for_super_admin_target(current_user, user)
    
    if updates.email is not None:
        existing = db.query(User).filter(User.email == updates.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = updates.email
        
    if updates.username is not None:
        existing = db.query(User).filter(User.username == updates.username, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = updates.username

    if updates.full_name is not None:
        user.full_name = updates.full_name
        
    if updates.is_active is not None:
        # Prevent deactivating yourself
        if user.id == current_user.id and not updates.is_active:
             raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        user.is_active = updates.is_active
        
    if updates.role_id is not None:
        role = db.query(Role).filter(Role.id == updates.role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail=f"Role {updates.role_id} not found")
        _require_superuser_for_super_admin_role(current_user, role)
        user.role_id = updates.role_id
        user.is_superuser = _is_super_admin_role(role)
        
    if updates.password is not None:
        user.hashed_password = get_password_hash(updates.password)
        
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=PaginatedResponse[UserResponse])
def list_users(
    search: Optional[str] = Query(None, description="Filtro por nombre, usuario o email"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Resultados por página"),
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db)
):
    """Lista usuarios con filtrado y paginación."""
    query = db.query(User)

    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(like_term),
                User.full_name.ilike(like_term),
                User.email.ilike(like_term),
            )
        )

    total = query.count()
    offset = (page - 1) * per_page
    users = (
        query.order_by(User.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    pages = math.ceil(total / per_page) if total else 0

    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db)
):
    """
    Delete a user (superuser only).
    
    Args:
        - user_id: ID of user to delete
        
    Raises:
        - 404: If user not found
        - 400: If trying to delete yourself
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    _require_superuser_for_super_admin_target(current_user, user)
    
    try:
        db.delete(user)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )


@router.get("/permissions", response_model=PaginatedResponse[PermissionResponse])
def list_permissions(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(100, ge=10, le=500, description="Resultados por página"),
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db)
):
    """Lista todos los permisos registrados con paginación."""
    query = db.query(Permission).order_by(Permission.module.asc(), Permission.slug.asc())
    total = query.count()
    offset = (page - 1) * per_page
    permissions = query.offset(offset).limit(per_page).all()
    pages = math.ceil(total / per_page) if total else 0

    return PaginatedResponse(
        items=permissions,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
