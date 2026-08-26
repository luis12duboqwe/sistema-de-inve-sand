"""Canonical integrity guards for privileged user administration."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Role, User
from app.routers import auth_router as legacy_auth
from app.schemas import PaginatedResponse, UserResponse, UserUpdate


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _escape_like_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/users", response_model=PaginatedResponse[UserResponse])
def list_users_integrity(
    search: str | None = Query(None, description="Filtro por nombre, usuario o email"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Resultados por página"),
    current_user: User = Depends(check_permission("users:manage")),  # noqa: ARG001
    db: Session = Depends(get_db),
):
    """List users while treating LIKE metacharacters in search as literals."""
    query = db.query(User)

    if search:
        like_term = f"%{_escape_like_literal(search)}%"
        query = query.filter(
            or_(
                User.username.ilike(like_term, escape="\\"),
                User.full_name.ilike(like_term, escape="\\"),
                User.email.ilike(like_term, escape="\\"),
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


def lock_and_guard_super_admin_continuity(
    db: Session,
    *,
    current_user: User,
    target_user: User,
    removes_active_super_admin: bool,
) -> None:
    """Serialize operations that could remove an active Super Admin."""
    if not removes_active_super_admin or not target_user.is_superuser or not target_user.is_active:
        return

    # Lock the complete active Super Admin set. Concurrent demotions,
    # deactivations and deletions then serialize instead of all observing the
    # same pre-change administrator count.
    active_super_admins = (
        db.query(User)
        .populate_existing()
        .filter(User.is_superuser == True, User.is_active == True)
        .order_by(User.id.asc())
        .with_for_update()
        .all()
    )

    # The request may have waited while another transaction changed or even
    # deleted the actor/target. Re-query with populate_existing so identity-map
    # state cannot preserve stale privileges after the row locks are acquired.
    fresh_actor = (
        db.query(User)
        .populate_existing()
        .filter(User.id == current_user.id)
        .first()
    )
    if not fresh_actor or not fresh_actor.is_active or not fresh_actor.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta ya no tiene privilegios de Super Admin",
        )

    fresh_target = (
        db.query(User)
        .populate_existing()
        .filter(User.id == target_user.id)
        .first()
    )
    if not fresh_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {target_user.id} not found",
        )

    if fresh_target.is_active and fresh_target.is_superuser and len(active_super_admins) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede dejar el sistema sin Super Admin activo",
        )


def _guard_role_change(
    db: Session,
    *,
    current_user: User,
    target_user: User,
    new_role: Role,
) -> None:
    lock_and_guard_super_admin_continuity(
        db,
        current_user=current_user,
        target_user=target_user,
        removes_active_super_admin=not legacy_auth._is_super_admin_role(new_role),
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
    _guard_role_change(
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
    target: User | None = None
    selected_role: Role | None = None

    # Role demotion and deactivation can both remove an active Super Admin. Load
    # and guard the target once for either transition so the generic update route
    # cannot bypass the same continuity invariant as the dedicated endpoints.
    if updates.role_id is not None or updates.is_active is False:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

        legacy_auth._require_superuser_for_super_admin_target(current_user, target)

    if updates.role_id is not None:
        selected_role = db.query(Role).filter(Role.id == updates.role_id).first()
        if not selected_role:
            raise HTTPException(status_code=404, detail=f"Role {updates.role_id} not found")
        legacy_auth._require_superuser_for_super_admin_role(current_user, selected_role)

    if target is not None:
        removes_active_super_admin = bool(
            updates.is_active is False
            or (selected_role is not None and not legacy_auth._is_super_admin_role(selected_role))
        )
        lock_and_guard_super_admin_continuity(
            db,
            current_user=current_user,
            target_user=target,
            removes_active_super_admin=removes_active_super_admin,
        )

    return legacy_auth.update_user_admin(
        user_id=user_id,
        updates=updates,
        current_user=current_user,
        db=db,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_integrity(
    user_id: int,
    current_user: User = Depends(check_permission("users:manage")),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    legacy_auth._require_superuser_for_super_admin_target(current_user, target)
    lock_and_guard_super_admin_continuity(
        db,
        current_user=current_user,
        target_user=target,
        removes_active_super_admin=True,
    )

    return legacy_auth.delete_user(
        user_id=user_id,
        current_user=current_user,
        db=db,
    )
