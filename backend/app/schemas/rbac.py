"""Esquemas Pydantic para usuarios, roles y permisos (RBAC)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


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

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
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


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    role: Optional[RoleResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
