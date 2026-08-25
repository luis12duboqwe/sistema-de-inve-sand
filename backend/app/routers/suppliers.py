import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import check_permission
from app.database import get_db
from app.models import Supplier, User
from app.schemas import SupplierCreate, SupplierResponse, SupplierUpdate
from app.utils.supplier_names import normalize_supplier_name, supplier_name_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _escape_like_literal(value: str) -> str:
    """Escape SQL LIKE metacharacters so supplier search is literal text."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _supplier_name_filter(value: str):
    """Match the canonical supplier identity used by the database unique index."""
    return Supplier.nombre_key_hash == supplier_name_hash(value)


def _supplier_integrity_error(
    db: Session,
    name: str,
    *,
    exclude_supplier_id: Optional[int] = None,
) -> HTTPException:
    """Translate only a proven normalized-name collision into a duplicate error."""
    clean_name = normalize_supplier_name(name)
    query = db.query(Supplier).filter(_supplier_name_filter(clean_name))
    if exclude_supplier_id is not None:
        query = query.filter(Supplier.id != exclude_supplier_id)

    if query.first() is not None:
        return HTTPException(
            status_code=400,
            detail=f"El proveedor '{clean_name}' ya existe",
        )

    logger.warning(
        "Supplier write hit an unrelated integrity conflict (supplier_id=%s)",
        exclude_supplier_id,
    )
    return HTTPException(
        status_code=409,
        detail="Conflicto de integridad al guardar el proveedor. Reintente la operación.",
    )


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
        updated_at=supplier.updated_at,
    )


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=201,
    dependencies=[Depends(check_permission("inventory:edit"))],
)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit")),
):
    """Crea un nuevo proveedor global del negocio."""
    try:
        nombre_limpio = normalize_supplier_name(supplier.nombre)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Friendly preflight; the database hash uniqueness is authoritative under
    # concurrent requests and protects every ORM write path on both DB engines.
    existing = db.query(Supplier).filter(_supplier_name_filter(nombre_limpio)).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"El proveedor '{nombre_limpio}' ya existe",
        )

    try:
        db_supplier = Supplier(
            profile_id=supplier.profile_id,
            nombre=nombre_limpio,
            contacto=supplier.contacto,
            telefono=supplier.telefono,
            email=supplier.email,
            direccion=supplier.direccion,
            notas=supplier.notas,
            activo=supplier.activo,
        )
        db.add(db_supplier)
        db.commit()
        db.refresh(db_supplier)
        return _serialize_supplier(db_supplier)
    except IntegrityError:
        db.rollback()
        raise _supplier_integrity_error(db, nombre_limpio)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error creating supplier")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al crear proveedor.",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        logger.exception("Error al crear proveedor")
        raise HTTPException(
            status_code=500,
            detail=(
                "Error interno al crear el proveedor. Intente nuevamente o "
                "contacte al administrador."
            ),
        )


@router.get(
    "",
    response_model=dict,
    dependencies=[Depends(check_permission("inventory:view"))],
)
def list_suppliers(
    include_inactive: bool = Query(False, description="Incluir proveedores inactivos"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    """Lista proveedores globales con filtros y paginación."""
    query = db.query(Supplier)

    # ``%``, ``_`` y ``\`` son texto de usuario, no sintaxis LIKE.
    if search:
        search_pattern = f"%{_escape_like_literal(search)}%"
        query = query.filter(Supplier.nombre.ilike(search_pattern, escape="\\"))

    if not include_inactive:
        query = query.filter(Supplier.activo == True)  # noqa: E712

    query = query.order_by(Supplier.nombre)
    total = query.count()
    pages = (total + per_page - 1) // per_page
    supplier_items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [_serialize_supplier(item) for item in supplier_items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    dependencies=[Depends(check_permission("inventory:view"))],
)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    """Obtiene un proveedor por su ID."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado",
        )
    return _serialize_supplier(supplier)


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    dependencies=[Depends(check_permission("inventory:edit"))],
)
def update_supplier(
    supplier_id: int,
    updates: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit")),
):
    """Actualiza un proveedor existente."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado",
        )

    integrity_name = supplier.nombre
    try:
        update_data = updates.model_dump(exclude_unset=True)
        if "nombre" in update_data:
            try:
                nuevo_nombre = normalize_supplier_name(update_data["nombre"])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            integrity_name = nuevo_nombre
            target_hash = supplier_name_hash(nuevo_nombre)
            if target_hash != supplier.nombre_key_hash:
                existing = (
                    db.query(Supplier)
                    .filter(
                        Supplier.nombre_key_hash == target_hash,
                        Supplier.id != supplier_id,
                    )
                    .first()
                )
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El proveedor '{nuevo_nombre}' ya existe",
                    )
            update_data["nombre"] = nuevo_nombre

        for key, value in update_data.items():
            setattr(supplier, key, value)

        db.commit()
        db.refresh(supplier)
        return _serialize_supplier(supplier)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise _supplier_integrity_error(
            db,
            integrity_name,
            exclude_supplier_id=supplier_id,
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error updating supplier")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al actualizar proveedor.",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        logger.exception("Error al actualizar proveedor %s", supplier_id)
        raise HTTPException(
            status_code=500,
            detail=(
                "Error interno al actualizar el proveedor. Intente nuevamente o "
                "contacte al administrador."
            ),
        )


@router.delete(
    "/{supplier_id}",
    status_code=204,
    dependencies=[Depends(check_permission("inventory:edit"))],
)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit")),
):
    """Elimina un proveedor sin productos asociados."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Proveedor con ID {supplier_id} no encontrado",
        )

    from app.models import Product

    product_count = db.query(Product).filter(Product.supplier_id == supplier_id).count()
    if product_count > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede eliminar el proveedor porque tiene {product_count} "
                "productos asociados. Desactívelo usando 'activo=false' en su lugar."
            ),
        )

    try:
        db.delete(supplier)
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede eliminar el proveedor debido a dependencias en la base "
                "de datos."
            ),
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error deleting supplier")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al eliminar proveedor.",
        )
    except Exception:
        db.rollback()
        logger.exception("Error al eliminar proveedor %s", supplier_id)
        raise HTTPException(
            status_code=500,
            detail=(
                "Error interno al eliminar el proveedor. Intente nuevamente o "
                "contacte al administrador."
            ),
        )
