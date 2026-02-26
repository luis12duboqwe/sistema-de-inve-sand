from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging
from app import models, schemas
from app.database import get_db
from app.auth import check_permission
import json

router = APIRouter(prefix="/api/sales-profiles", tags=["sales_profiles"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[schemas.SalesProfileResponse], dependencies=[Depends(check_permission("settings:view"))])
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
    
    # Convertir a diccionarios para evitar modificar los objetos de SQLAlchemy
    result = []
    for profile in profiles:
        profile_dict = {
            "id": profile.id,
            "name": profile.name,
            "slug": profile.slug,
            "tipo": profile.tipo,
            "active": profile.active,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "canales": json.loads(profile.canales) if profile.canales else [],
            "configuracion": json.loads(profile.configuracion) if profile.configuracion else {}
        }
        result.append(profile_dict)
    
    return result


@router.get("/{profile_id}", response_model=schemas.SalesProfileResponse, dependencies=[Depends(check_permission("settings:view"))])
def get_sales_profile(profile_id: int, db: Session = Depends(get_db)):
    """Obtener un perfil de venta específico"""
    profile = db.query(models.SalesProfile).filter(models.SalesProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    # Convertir a diccionario para evitar modificar el objeto ORM
    profile_dict = {
        "id": profile.id,
        "name": profile.name,
        "slug": profile.slug,
        "tipo": profile.tipo,
        "active": profile.active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "canales": [],
        "configuracion": {}
    }

    # Convertir JSON strings a objetos
    if profile.canales:
        try:
            profile_dict["canales"] = json.loads(profile.canales)
        except:
            pass
    
    if profile.configuracion:
        try:
            profile_dict["configuracion"] = json.loads(profile.configuracion)
        except:
            pass
    
    return profile_dict


@router.get("/slug/{slug}", response_model=schemas.SalesProfileResponse, dependencies=[Depends(check_permission("settings:view"))])
def get_sales_profile_by_slug(slug: str, db: Session = Depends(get_db)):
    """Obtener un perfil de venta por su slug"""
    profile = db.query(models.SalesProfile).filter(models.SalesProfile.slug == slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    # Convertir a diccionario para evitar modificar el objeto ORM
    profile_dict = {
        "id": profile.id,
        "name": profile.name,
        "slug": profile.slug,
        "tipo": profile.tipo,
        "active": profile.active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "canales": [],
        "configuracion": {}
    }

    # Convertir JSON strings a objetos
    if profile.canales:
        try:
            profile_dict["canales"] = json.loads(profile.canales)
        except:
            pass
    
    if profile.configuracion:
        try:
            profile_dict["configuracion"] = json.loads(profile.configuracion)
        except:
            pass
    
    return profile_dict


@router.post("", response_model=schemas.SalesProfileResponse, status_code=201, dependencies=[Depends(check_permission("settings:edit"))])
def create_sales_profile(
    profile: schemas.SalesProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(check_permission("settings:edit"))
):
    """Crear un nuevo perfil de venta"""
    # Verificar que el slug sea único (case-insensitive para evitar duplicados tipo 'Bot-1' vs 'bot-1')
    existing = db.query(models.SalesProfile).filter(
        models.SalesProfile.slug.ilike(profile.slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un perfil con el slug '{profile.slug}' (la comparación ignora mayúsculas/minúsculas)"
        )
    
    try:
        # Convertir listas y dicts a JSON strings
        profile_data = profile.model_dump()
        if profile_data.get('canales'):
            profile_data['canales'] = json.dumps(profile_data['canales'])
        if profile_data.get('configuracion'):
            profile_data['configuracion'] = json.dumps(profile_data['configuracion'])
        
        db_profile = models.SalesProfile(**profile_data)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        
        # Convertir de vuelta para la respuesta
        if db_profile.canales:
            db_profile.canales = json.loads(db_profile.canales)
        else:
            db_profile.canales = []
        
        if db_profile.configuracion:
            db_profile.configuracion = json.loads(db_profile.configuracion)
        else:
            db_profile.configuracion = {}
        
        return db_profile
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
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
    
    try:
        update_data = profile.model_dump(exclude_unset=True)
        
        # Validar slug único si se está actualizando (case-insensitive)
        if 'slug' in update_data and update_data['slug'] != db_profile.slug:
            existing = db.query(models.SalesProfile).filter(
                models.SalesProfile.slug.ilike(update_data['slug']),
                models.SalesProfile.id != profile_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe otro perfil con el slug '{update_data['slug']}' (la comparación ignora mayúsculas/minúsculas)"
                )
        
        # Convertir listas y dicts a JSON strings
        if 'canales' in update_data and update_data['canales'] is not None:
            update_data['canales'] = json.dumps(update_data['canales'])
        if 'configuracion' in update_data and update_data['configuracion'] is not None:
            update_data['configuracion'] = json.dumps(update_data['configuracion'])
        
        for field, value in update_data.items():
            setattr(db_profile, field, value)
        
        db.commit()
        db.refresh(db_profile)
    
        # Convertir de vuelta para la respuesta
        if db_profile.canales:
            db_profile.canales = json.loads(db_profile.canales)
        else:
            db_profile.canales = []
        
        if db_profile.configuracion:
            db_profile.configuracion = json.loads(db_profile.configuracion)
        else:
            db_profile.configuracion = {}
        
        return db_profile
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
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
    except Exception as e:
        db.rollback()
        logger.exception("Error al eliminar perfil de venta")
        raise HTTPException(status_code=500, detail="Error interno al eliminar perfil de venta. Intente nuevamente o contacte al administrador.")


@router.get("/{profile_id}/orders", dependencies=[Depends(check_permission("orders:view"))])
def get_sales_profile_orders(
    profile_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Obtener todas las órdenes de un perfil de venta"""
    profile = db.query(models.SalesProfile).filter(models.SalesProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de venta no encontrado")
    
    orders = db.query(models.Order).filter(
        models.Order.sales_profile_id == profile_id
    ).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return orders
