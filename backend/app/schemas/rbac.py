"""Esquemas Pydantic para usuarios, roles y permisos (RBAC)."""

from datetime import datetime
import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


COMMON_PASSWORDS = {
    "password",
    "password123",
    "admin123",
    "123456789012",
    "qwerty123456",
}


def _validate_secure_password(value: str) -> str:
    if len(value) < 12:
        raise ValueError("Password must be at least 12 characters long")
    if value.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain at least one symbol")
    return value


class PermissionBase(BaseModel):
    slug: str
    description: str
    module: str


class PermissionResponse(PermissionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permissions: List[str]


class RoleResponse(RoleBase):
    id: int
    is_system_role: bool
    permissions: List[PermissionResponse]
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_secure_password(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not value.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return value


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _validate_secure_password(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not value.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return value


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    role: Optional[RoleResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
