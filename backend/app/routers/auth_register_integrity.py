"""Canonical integrity handler for administrative user registration."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import check_permission, get_password_hash
from app.database import get_db
from app.models import Role, User
from app.routers.auth_router import (
    _is_super_admin_role,
    _require_superuser_for_super_admin_role,
)
from app.schemas import UserCreate, UserResponse


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _duplicate_user_error(db: Session, username: str, email: str | None) -> HTTPException:
    """Translate the database uniqueness boundary into the existing API contract."""
    if db.query(User.id).filter(User.username == username).first():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    if email and db.query(User.id).filter(User.email == email).first():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Username or email already registered",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user_integrity(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("users:manage")),
):
    """Register a user while making PostgreSQL uniqueness race-safe."""
    if db.query(User.id).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    normalized_email = user.email.strip() if user.email else None
    if normalized_email and db.query(User.id).filter(User.email == normalized_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    selected_role = (
        db.query(Role).filter(Role.id == user.role_id).first() if user.role_id else None
    )
    if user.role_id and not selected_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {user.role_id} not found",
        )
    _require_superuser_for_super_admin_role(current_user, selected_role)

    db_user = User(
        username=user.username,
        email=normalized_email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
        role_id=user.role_id,
        is_superuser=_is_super_admin_role(selected_role),
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise _duplicate_user_error(db, user.username, normalized_email)
