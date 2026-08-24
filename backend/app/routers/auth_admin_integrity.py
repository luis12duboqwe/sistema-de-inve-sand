"""Canonical integrity guards for privileged user administration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Role, User
from app.routers import auth_router as legacy_auth
from app.schemas import UserResponse, UserUpdate


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _lock_and_guard_super_admin_demotion(
    db: Session,
    *,
    current_user: User,
    target_user: User,
    new_role: Role,
) -> None:
    """Prevent concurrent role changes from removing the final active Super Admin."""
    if not target_user.is_superuser or legacy_auth._is_super_admin_role(new_role):
        return

    # Lock the full Super Admin set so concurrent demotions serialize. Refreshing
    # actor/target after the lock also prevents a stale privileged identity from
    # continuing if another transaction changed it while this request waited.
    active_super_admins = (
        db.query(User)
        .filter(User.is_superuser == True, User.is_active == True)
        .order_by(User.id.asc())
        .with_for_update()
        .all()
    )
    db.refresh(current_user)
    if target_user.id != current_user.id:
        db.refresh(target_user)

    if not current_user.is_active or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta ya no tiene privilegios de Super Admin",
        )

    if target_user.is_active and target_user.is_superuser and len(active_super_admins) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede dejar el sistema sin Super Admin activo",
        )


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role_integrity(
    user_id: int,
    role_id: int = Query(..., description="ID of the new role"),
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role with ID {role_id} not found")

    legacy_auth._require_superuser_for_super_admin_target(current_user, target)
    legacy_auth._require_superuser_for_super_admin_role(current_user, role)
    _lock_and_guard_super_admin_demotion(
        db,
        current_user=current_user,
        target_user=target,
        new_role=role,
    )

    return legacy_auth.update_user_role(
        user_id=user_id,
        role_id=role_id,
        current_user=current_user,
        db=db,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_admin_integrity(
    user_id: int,
    updates: UserUpdate,
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db),
):
    if updates.role_id is not None:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

        role = db.query(Role).filter(Role.id == updates.role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail=f"Role {updates.role_id} not found")

        legacy_auth._require_superuser_for_super_admin_target(current_user, target)
        legacy_auth._require_superuser_for_super_admin_role(current_user, role)
        _lock_and_guard_super_admin_demotion(
            db,
            current_user=current_user,
            target_user=target,
            new_role=role,
        )

    return legacy_auth.update_user_admin(
        user_id=user_id,
        updates=updates,
        current_user=current_user,
        db=db,
    )
