from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, UserLocationAccess


def _is_privileged_role_without_scope(user: User) -> bool:
    """Return True for system roles that should see all locations by default.

    This fallback only applies when there are no explicit location-access rows.
    """
    role = getattr(user, "role", None)
    if getattr(role, "is_system_role", False):
        return True

    role_name = (getattr(role, "name", "") or "").strip().lower()
    return role_name in {
        "admin",
        "super admin",
        "superadmin",
        "super-admin",
        "gerente",
        "vendedor",
        "invitado",
    }


def get_accessible_location_ids(db: Session, user: User, capability: str = "can_view") -> list[int] | None:
    if user.is_superuser:
        return None

    access_rows = db.query(UserLocationAccess).filter(UserLocationAccess.user_id == user.id).all()
    if not access_rows:
        if _is_privileged_role_without_scope(user):
            return None
        return []

    return [
        access.location_id
        for access in access_rows
        if bool(getattr(access, capability, False) or getattr(access, "can_edit", False))
    ]


def user_has_location_access(db: Session, user: User, location_id: int, capability: str = "can_view") -> bool:
    if user.is_superuser:
        return True

    access_rows = db.query(UserLocationAccess).filter(UserLocationAccess.user_id == user.id).all()
    if not access_rows:
        if _is_privileged_role_without_scope(user):
            return True
        return False

    row = next((access for access in access_rows if access.location_id == location_id), None)
    if not row:
        return False

    return bool(getattr(row, capability, False) or getattr(row, "can_edit", False))


def require_location_access(db: Session, user: User, location_id: int, capability: str = "can_view") -> None:
    if not user_has_location_access(db, user, location_id, capability):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tiene acceso a la ubicación {location_id} para {capability}",
        )