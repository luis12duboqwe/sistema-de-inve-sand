import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_active_user, check_permission
from app.models import Supplier, Profile, User
from app.schemas import SupplierCreate, SupplierUpdate, SupplierResponse

logger = logging.getLogger(__name__)

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


@router.post("", response_model=SupplierResponse, status_code=201, dependencies=[Depends(check_permission("inventory:edit"))])
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit"))
):
    """
    Crea un nuevo proveedor.
    
    V2.0: Los proveedores son globales del negocio, no pertenecen a un perfil específico.
    
    Args:
        - supplier: Datos del proveedor a crear
        - db: Sesión de base de datos
        
    Returns:
        Proveedor creado
    """
    # Validar que el nombre sea único (case-insensitive)
    nombre_limpio = (supplier.nombre or "").strip()
    if not nombre_limpio:
        raise HTTPException(
            status_code=400,
            detail="El nombre del proveedor no puede estar vacío"
        )
    
    existing = db.query(Supplier).filter(
        func.lower(Supplier.nombre) == nombre_limpio.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"El proveedor '{nombre_limpio}' ya existe"
        )
    
    # Crear proveedor directamente (sin validación de profile)
    # V2.0: profile_id ahora es nullable, proveedores son globales
    try:
        db_supplier = Supplier(
            profile_id=supplier.profile_id,  # V2.0: Nullable, proveedores globales no necesitan profile
            nombre=nombre_limpio,
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
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error de integridad: El proveedor ya existe."
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error creating supplier")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al crear proveedor."
        )
    except Exception:
        db.rollback()
        logger.exception("Error al crear proveedor")
        raise HTTPException(
            status_code=500,
            detail="Error interno al crear el proveedor. Intente nuevamente o contacte al administrador."
        )


@router.get("", response_model=dict, dependencies=[Depends(check_permission("inventory:view"))])
def list_suppliers(
    include_inactive: bool = Query(False, description="Incluir proveedores inactivos"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view"))
):
    """
    Lista proveedores con filtros opcionales.
    
    V2.0: Los proveedores son globales y visibles para todo el negocio.
    
    Parámetros:
    - include_inactive: Incluir proveedores inactivos
    - search: Buscar por nombre
    - page: Número de página
    - per_page: Resultados por página
    """
    query = db.query(Supplier)
    
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
    pages = (total + per_page - 1) // per_page
    
    suppliers = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "items": [_serialize_supplier(s) for s in suppliers],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }


@router.get("/{supplier_id}", response_model=SupplierResponse, dependencies=[Depends(check_permission("inventory:view"))])
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view"))
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


@router.put("/{supplier_id}", response_model=SupplierResponse, dependencies=[Depends(check_permission("inventory:edit"))])
def update_supplier(
    supplier_id: int,
    updates: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit"))
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
    
    try:
        # Aplicar actualizaciones
        update_data = updates.model_dump(exclude_unset=True)
        
        # Validar nombre único si se está actualizando (case-insensitive)
        if 'nombre' in update_data:
            nuevo_nombre = (update_data['nombre'] or "").strip()
            if not nuevo_nombre:
                raise HTTPException(
                    status_code=400,
                    detail="El nombre del proveedor no puede estar vacío"
                )
            if nuevo_nombre.lower() != supplier.nombre.lower():
                existing = db.query(Supplier).filter(
                    func.lower(Supplier.nombre) == nuevo_nombre.lower(),
                    Supplier.id != supplier_id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El proveedor '{nuevo_nombre}' ya existe"
                    )
            update_data['nombre'] = nuevo_nombre
        
        for key, value in update_data.items():
            setattr(supplier, key, value)
        
        db.commit()
        db.refresh(supplier)
        
        return _serialize_supplier(supplier)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error de integridad: El nombre de proveedor ya existe."
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error updating supplier")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al actualizar proveedor."
        )
    except Exception:
        db.rollback()
        logger.exception("Error al actualizar proveedor %s", supplier_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al actualizar el proveedor. Intente nuevamente o contacte al administrador."
        )


@router.delete("/{supplier_id}", status_code=204, dependencies=[Depends(check_permission("inventory:edit"))])
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit"))
):
    """
    Elimina un proveedor.
    
    Advertencia: Si el proveedor tiene productos asociados, su supplier_id será establecido a NULL.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado"
        )
    
    # Verificar si tiene productos asociados y advertir
    from app.models import Product
    product_count = db.query(Product).filter(Product.supplier_id == supplier_id).count()
    if product_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el proveedor porque tiene {product_count} productos asociados. Desactívelo usando 'activo=false' en su lugar."
        )
    
    try:
        db.delete(supplier)
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el proveedor debido a dependencias en la base de datos."
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error deleting supplier")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al eliminar proveedor."
        )
    except Exception:
        db.rollback()
        logger.exception("Error al eliminar proveedor %s", supplier_id)
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar el proveedor. Intente nuevamente o contacte al administrador."
        )
