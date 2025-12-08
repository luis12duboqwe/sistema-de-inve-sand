from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Supplier, Profile
from app.schemas import SupplierCreate, SupplierResponse, SupplierUpdate, PaginatedResponse

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _serialize_supplier(supplier: Supplier) -> SupplierResponse:
    """Serializa un Supplier a SupplierResponse"""
    return SupplierResponse(
        id=supplier.id,
        profile_id=supplier.profile_id,
        nombre=supplier.nombre,
        contacto=supplier.contacto,
        telefono=supplier.telefono,
        email=supplier.email,
        direccion=supplier.direccion,
        notas=supplier.notas,
        activo=supplier.activo,
        created_at=supplier.created_at,
        updated_at=supplier.updated_at
    )


@router.post("", response_model=SupplierResponse, status_code=201)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo proveedor.
    
    Args:
        - supplier: Datos del proveedor a crear
        - db: Sesión de base de datos
        
    Returns:
        Proveedor creado
    """
    # Validar que el perfil exista
    profile = db.query(Profile).filter(Profile.id == supplier.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Perfil con ID {supplier.profile_id} no encontrado"
        )
    
    db_supplier = Supplier(
        profile_id=supplier.profile_id,
        nombre=supplier.nombre,
        contacto=supplier.contacto,
        telefono=supplier.telefono,
        email=supplier.email,
        direccion=supplier.direccion,
        notas=supplier.notas,
        activo=supplier.activo
    )
    
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    
    return _serialize_supplier(db_supplier)


@router.get("", response_model=PaginatedResponse[SupplierResponse])
def list_suppliers(
    profile_id: Optional[int] = Query(None, description="Filtrar por ID de perfil"),
    include_inactive: bool = Query(False, description="Incluir proveedores inactivos"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista proveedores con filtros opcionales.
    
    Parámetros:
    - profile_id: Filtrar por perfil
    - include_inactive: Incluir proveedores inactivos
    - search: Buscar por nombre
    - page: Número de página
    - per_page: Resultados por página
    """
    query = db.query(Supplier)
    
    # Filtro por perfil
    if profile_id:
        query = query.filter(Supplier.profile_id == profile_id)
    
    # Filtro por búsqueda
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(Supplier.nombre.ilike(search_pattern))
    
    # Filtro por estado
    if not include_inactive:
        query = query.filter(Supplier.activo == True)
    
    # Ordenar por nombre
    query = query.order_by(Supplier.nombre)
    
    # Paginación
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    
    suppliers = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return PaginatedResponse(
        items=[_serialize_supplier(s) for s in suppliers],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un proveedor por su ID.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado"
        )
    
    return _serialize_supplier(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    updates: SupplierUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un proveedor existente.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado"
        )
    
    # Aplicar actualizaciones
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)
    
    db.commit()
    db.refresh(supplier)
    
    return _serialize_supplier(supplier)


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un proveedor.
    
    Nota: Los productos asociados al proveedor tendrán su supplier_id establecido a NULL.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado"
        )
    
    db.delete(supplier)
    db.commit()
    
    return None
