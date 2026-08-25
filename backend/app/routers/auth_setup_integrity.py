"""Atomic first-admin setup that cannot create two initial Super Admins."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_password_hash
from app.config import settings
from app.database import get_db
from app.models import Permission, Role, SystemConfig, User
from app.routers.auth_router import SYSTEM_PERMISSIONS, SYSTEM_ROLE_CONFIG
from app.schemas import Token, UserCreate


router = APIRouter(prefix="/api/auth", tags=["authentication"])
_INITIAL_SETUP_CLAIM_KEY = "initial_admin_setup"


def _ensure_default_rbac_transactional(db: Session) -> None:
    """Create/update canonical RBAC without committing the caller transaction."""
    permission_by_slug = {
        permission.slug: permission for permission in db.query(Permission).all()
    }

    for definition in SYSTEM_PERMISSIONS:
        permission = permission_by_slug.get(definition["slug"])
        if permission is not None:
            continue
        permission = Permission(
            slug=definition["slug"],
            description=definition["description"],
            module=definition["module"],
        )
        db.add(permission)
        db.flush()
        permission_by_slug[permission.slug] = permission

    for definition in SYSTEM_ROLE_CONFIG:
        role = db.query(Role).filter(Role.name == definition["name"]).first()
        role_permissions = [
            permission_by_slug[slug]
            for slug in definition["permission_slugs"]
            if slug in permission_by_slug
        ]

        if role is None:
            role = Role(
                name=definition["name"],
                description=definition["description"],
                is_system_role=definition["is_system_role"],
            )
            role.permissions = role_permissions
            db.add(role)
            continue

        existing_slugs = {permission.slug for permission in (role.permissions or [])}
        required_slugs = {permission.slug for permission in role_permissions}
        if not required_slugs.issubset(existing_slugs):
            role.permissions = role_permissions
        if not role.is_system_role:
            role.is_system_role = definition["is_system_role"]

    db.flush()


def _claim_initial_setup(db: Session, username: str) -> None:
    """Reserve first setup using a database uniqueness boundary."""
    claim = SystemConfig(
        key=_INITIAL_SETUP_CLAIM_KEY,
        value=username,
        description="Atomic claim for the first Super Admin setup",
        updated_by="system",
    )
    db.add(claim)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System already initialized. Use login.",
        ) from exc


@router.post("/setup", response_model=Token)
def setup_initial_admin_integrity(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    """Create exactly one initial Super Admin as one atomic transaction."""
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System already initialized. Use login.",
        )

    # Two concurrent requests can both observe zero users. The unique setup claim
    # is therefore acquired before RBAC/user writes and remains uncommitted until
    # the first admin itself is committed. A failed setup rolls the claim back.
    _claim_initial_setup(db, user.username)

    try:
        _ensure_default_rbac_transactional(db)
        admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
        if admin_role is None:
            raise RuntimeError("No se pudo crear el rol Super Admin")

        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
            full_name=user.full_name,
            is_superuser=True,
            is_active=True,
            role_id=admin_role.id,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": db_user,
    }


__all__ = ["router", "setup_initial_admin_integrity"]
