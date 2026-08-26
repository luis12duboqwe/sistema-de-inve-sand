from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging
from app import models, schemas
from app.database import get_db
from app.auth import check_permission, check_any_permission
from app.sales_profile_identity import normalize_sales_profile_slug, sales_profile_slug_hash
from app.sales_profile_lookup import find_sales_profile_by_slug
from app.utils.location_access import get_accessible_location_ids
from app.utils.sales_profile_config import prepare_config_for_storage, serialize_sales_profile

router = APIRouter(prefix="/api/sales-profiles", tags=["sales_profiles"])
logger = logging.getLogger(__name__)


def _slug_filter(value: str):
    return models.SalesProfile.slug_key_hash == sales_profile_slug_hash(value)


def _slug_duplicate_detail(slug: str, *, another: bool = False) -> str:
    prefix = "Ya existe otro perfil" if another else "Ya existe un perfil"
    return (
        f"{prefix} con el slug '{slug}' "
        "(la comparación ignora mayúsculas/minúsculas)"
    )


def _sales_profile_integrity_error(
    db: Session,
    slug: str,
    *,
    exclude_profile_id: Optional[int] = None,
) -> HTTPException:
    clean_slug = normalize_sales_profile_slug(slug)
    query = db.query(models.SalesProfile).filter(_slug_filter(clean_slug))
    if exclude_profile_id is not None:
        query = query.filter(models.SalesProfile.id != exclude_profile_id)

    if query.first() is not None:
        return HTTPException(
            status_code=400,
            detail=_slug_duplicate_detail(
                clean_slug,
                another=exclude_profile_id is not None,
            ),
        )

    logger.warning(
        "Sales profile write hit an unrelated integrity conflict (profile_id=%s)",
        exclude_profile_id,
    )
    return HTTPException(
        status_code=409,
        detail="Conflicto de integridad al guardar el perfil de venta. Reintente la operación.",
    )


@router.get("", response_model=List[schemas.SalesProfileResponse], dependencies=[Depends(check_any_permission("settings:view", "orders:view", "orders:create"))])
def get_sales_profiles(
    skip: int = 0,
    limit: int = 100,
    active: Optional[bool] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Obtener todos los perfiles de venta (vendedores, bots, etc.)"""
    query = db.query(models.SalesProfile)
    
    if active is not None:
        query = query.filter(models.SalesProfile.active == active)
    
    if tipo:
        query = query.filter(models.SalesProfile.tipo == tipo)
    
    profiles = query.order_by(models.SalesProfile.name).offset(skip).limit(limit).all()
    
    return [serialize_sales_profile(profile) for profile in profiles]


@router.get("/slug/{slug}", response_model=schemas.SalesProfileResponse, dependencies=[Depends(check_any_permission("settings:view", "orders:view", "orders:create"))])
def get_sales_profile_by_slug(slug: str, db: Session = Depends(get_db)):
    """Obtener un perfil de venta por su slug con identidad case-insensitive estable."""
    profile = find_sales_profile_by_slug(db, slug)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    return serialize_sales_profile(profile)


@router.get("/{profile_id}", response_model=schemas.SalesProfileResponse, dependencies=[Depends(check_any_permission("settings:view", "orders:view", "orders:create"))])
def get_sales_profile(profile_id: int, db: Session = Depends(get_db)):
    """Obtener un perfil de venta específico"""
    profile = db.query(models.SalesProfile).filter(models.SalesProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    return serialize_sales_profile(profile)


@router.post("", response_model=schemas.SalesProfileResponse, status_code=201, dependencies=[Depends(check_permission("settings:edit"))])
def create_sales_profile(
    profile: schemas.SalesProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_permission("settings:edit"))
):
    """Crear un nuevo perfil de venta"""
    try:
        clean_slug = normalize_sales_profile_slug(profile.slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = find_sales_profile_by_slug(db, clean_slug)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=_slug_duplicate_detail(clean_slug),
        )
    
    try:
        # Convertir listas y dicts a JSON strings
        profile_data = profile.model_dump()
        profile_data['slug'] = clean_slug
        if profile_data.get('canales'):
            profile_data['canales'] = json.dumps(profile_data['canales'])
        if profile_data.get('configuracion'):
            profile_data['configuracion'] = json.dumps(prepare_config_for_storage(profile_data['configuracion']))
        
        db_profile = models.SalesProfile(**profile_data)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        
        return serialize_sales_profile(db_profile)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise _sales_profile_integrity_error(db, clean_slug)
    except Exception:
        db.rollback()
        logger.exception("Error al crear perfil de venta")
        raise HTTPException(status_code=500, detail="Error interno al crear perfil de venta. Intente nuevamente o contacte al administrador.")


@router.put("/{profile_id}", response_model=schemas.SalesProfileResponse, dependencies=[Depends(check_permission("settings:edit"))])
def update_sales_profile(
    profile_id: int,
    profile: schemas.SalesProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_permission("settings:edit"))
):
    """Actualizar un perfil de venta existente"""
    db_profile = db.query(models.SalesProfile).filter(models.SalesProfile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")

    integrity_slug = db_profile.slug
    
    try:
        update_data = profile.model_dump(exclude_unset=True)
        
        if 'slug' in update_data:
            submitted_slug = update_data['slug']
            if submitted_slug == db_profile.slug:
                # A migrated historical display slug can contain outer spaces or
                # legacy casing. Re-sending that exact value while editing another
                # field must not silently rewrite the persisted display slug.
                update_data.pop('slug')
            else:
                try:
                    clean_slug = normalize_sales_profile_slug(submitted_slug)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc

                integrity_slug = clean_slug
                target_hash = sales_profile_slug_hash(clean_slug)
                if target_hash != db_profile.slug_key_hash:
                    existing = find_sales_profile_by_slug(db, clean_slug)
                    if existing and existing.id != profile_id:
                        raise HTTPException(
                            status_code=400,
                            detail=_slug_duplicate_detail(clean_slug, another=True),
                        )
                update_data['slug'] = clean_slug
        
        # Convertir listas y dicts a JSON strings
        if 'canales' in update_data and update_data['canales'] is not None:
            update_data['canales'] = json.dumps(update_data['canales'])
        if 'configuracion' in update_data and update_data['configuracion'] is not None:
            update_data['configuracion'] = json.dumps(
                prepare_config_for_storage(update_data['configuracion'], db_profile.configuracion)
            )
        
        for field, value in update_data.items():
            setattr(db_profile, field, value)
        
        db.commit()
        db.refresh(db_profile)
    
        return serialize_sales_profile(db_profile)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise _sales_profile_integrity_error(
            db,
            integrity_slug,
            exclude_profile_id=profile_id,
        )
    except Exception:
        db.rollback()
        logger.exception("Error al actualizar perfil de venta")
        raise HTTPException(status_code=500, detail="Error interno al actualizar perfil de venta. Intente nuevamente o contacte al administrador.")


@router.delete("/{profile_id}", status_code=204, dependencies=[Depends(check_permission("settings:edit"))])
def delete_sales_profile(
    profile_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_permission("settings:edit"))
):
    """Eliminar un perfil de venta"""
    db_profile = db.query(models.SalesProfile).filter(models.SalesProfile.id == profile_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    # Verificar que no tenga órdenes
    order_count = db.query(models.Order).filter(models.Order.sales_profile_id == profile_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el perfil porque tiene {order_count} órdenes históricas asociadas. Use 'active=false' para desactivarlo en lugar de eliminarlo."
        )
    
    try:
        db.delete(db_profile)
        db.commit()
        return None
    except Exception:
        db.rollback()
        logger.exception("Error al eliminar perfil de venta")
        raise HTTPException(status_code=500, detail="Error interno al eliminar perfil de venta. Intente nuevamente o contacte al administrador.")


@router.get("/{profile_id}/orders", dependencies=[Depends(check_permission("orders:view"))])
def get_sales_profile_orders(
    profile_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(check_permission("orders:view")),
):
    """Obtener todas las órdenes de un perfil de venta"""
    profile = db.query(models.SalesProfile).filter(models.SalesProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    query = db.query(models.Order).filter(
        models.Order.sales_profile_id == profile_id
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        query = query.filter(models.Order.source_location_id.in_(accessible_location_ids))
    orders = query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return orders
