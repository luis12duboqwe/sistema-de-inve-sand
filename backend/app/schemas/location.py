"""Esquemas relacionados con ubicaciones físicas, perfiles de venta y proveedores."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TipoUbicacionEnum(str, Enum):
    """Tipos de ubicación física."""

    TIENDA = "tienda"
    BODEGA = "bodega"
    OFICINA = "oficina"


class TipoSalesProfileEnum(str, Enum):
    """Tipos de perfil de venta."""

    BOT_IA = "bot_ia"
    VENDEDOR_HUMANO = "vendedor_humano"
    SISTEMA_AUTOMATICO = "sistema_automatico"


class LocationBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    tipo: TipoUbicacionEnum
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    activo: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    tipo: Optional[TipoUbicacionEnum] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None


class LocationResponse(LocationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SalesProfileBase(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    slug: str = Field(..., min_length=1, description="Slug no puede estar vacío")
    tipo: TipoSalesProfileEnum
    canales: Optional[List[str]] = None
    active: bool = True
    configuracion: Optional[Dict[str, str]] = None


class SalesProfileCreate(SalesProfileBase):
    pass


class SalesProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    slug: Optional[str] = Field(None, min_length=1, description="Slug no puede estar vacío si se proporciona")
    tipo: Optional[TipoSalesProfileEnum] = None
    canales: Optional[List[str]] = None
    active: Optional[bool] = None
    configuracion: Optional[Dict[str, str]] = None


class SalesProfileResponse(SalesProfileBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    slug: str = Field(..., min_length=1, description="Slug no puede estar vacío")
    active: bool = True
    settings: Optional[str] = None  # JSON string


class ProfileCreate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    slug: Optional[str] = Field(None, min_length=1, description="Slug no puede estar vacío si se proporciona")
    active: Optional[bool] = None
    settings: Optional[str] = None


class SupplierBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre no puede estar vacío")
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: bool = True


class SupplierCreate(SupplierBase):
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales


class SupplierUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, description="Nombre no puede estar vacío si se proporciona")
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    profile_id: Optional[int] = None  # V2.0: Deprecated, proveedores son globales
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "TipoUbicacionEnum",
    "TipoSalesProfileEnum",
    "LocationBase",
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "SalesProfileBase",
    "SalesProfileCreate",
    "SalesProfileUpdate",
    "SalesProfileResponse",
    "ProfileBase",
    "ProfileCreate",
    "ProfileResponse",
    "ProfileUpdate",
    "SupplierBase",
    "SupplierCreate",
    "SupplierUpdate",
    "SupplierResponse",
]
