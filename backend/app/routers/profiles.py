from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List
import math
import logging
from app.database import get_db
from app.models import Profile, User
from app.schemas import ProfileCreate, ProfileResponse, ProfileUpdate, PaginatedResponse
from app.auth import check_permission


router = APIRouter(prefix="/api/profiles", tags=["profiles"])
logger = logging.getLogger(__name__)

@router.get("", response_model=PaginatedResponse[ProfileResponse], dependencies=[Depends(check_permission("settings:view"))])
def list_profiles(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    include_inactive: bool = Query(False, description="Incluir perfiles inactivos"),
    db: Session = Depends(get_db)
):
    """
    Lista perfiles del sistema con paginación.
    
    Args:
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
        - include_inactive: Incluir perfiles inactivos (default: False)
        
    Returns:
        Respuesta paginada con lista de perfiles
    """
    query = db.query(Profile)
    
    if not include_inactive:
        query = query.filter(Profile.active == True)
    
    total = query.count()
    offset = (page - 1) * per_page
    
    profiles = query.offset(offset).limit(per_page).all()
    
    return PaginatedResponse(
        items=profiles,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )

@router.post("", response_model=ProfileResponse, status_code=201, dependencies=[Depends(check_permission("settings:edit"))])
def create_profile(
    profile: ProfileCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """
    Crea un nuevo perfil de negocio.
    
    Args:
        - profile: Datos del perfil a crear
        
    Returns:
        Perfil creado
        
    Raises:
        - 400: Si el slug ya existe (debe ser único)
    """
    existing = db.query(Profile).filter(Profile.slug == profile.slug).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un perfil con el slug '{profile.slug}'"
        )
    
    try:
        db_profile = Profile(**profile.model_dump())
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return db_profile
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error de integridad: Ya existe un perfil con el slug '{profile.slug}'"
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error creating profile")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al crear perfil."
        )
    except Exception as e:
        db.rollback()
        logger.exception("Error al crear perfil")
        raise HTTPException(status_code=500, detail="Error interno al crear perfil. Intente nuevamente o contacte al administrador.")

@router.get("/{profile_id}", response_model=ProfileResponse, dependencies=[Depends(check_permission("settings:view"))])
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un perfil por su ID.
    
    Args:
        - profile_id: ID del perfil
        
    Returns:
        Perfil solicitado
        
    Raises:
        - 404: Si el perfil no existe
    """
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"El perfil con ID {profile_id} no fue encontrado"
        )
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse, dependencies=[Depends(check_permission("settings:edit"))])
def update_profile(
    profile_id: int, 
    updates: ProfileUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """
    Actualiza un perfil existente.

    Args:
        - profile_id: ID del perfil a actualizar
        - updates: Campos a modificar (nombre/activo)

    Returns:
        Perfil actualizado

    Raises:
        - 404: Si el perfil no existe
    """
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"El perfil con ID {profile_id} no fue encontrado"
        )

    # Validar slug único si se está actualizando
    if updates.slug is not None and updates.slug != profile.slug:
        existing = db.query(Profile).filter(
            Profile.slug == updates.slug,
            Profile.id != profile_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe otro perfil con el slug '{updates.slug}'"
            )
        profile.slug = updates.slug

    if updates.name is not None:
        profile.name = updates.name
    if updates.active is not None:
        profile.active = updates.active

    try:
        db.commit()
        db.refresh(profile)
        return profile
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error de integridad: Ya existe otro perfil con el slug '{updates.slug}'"
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error updating profile")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al actualizar perfil."
        )
    except Exception as e:
        db.rollback()
        logger.exception("Error al actualizar perfil")
        raise HTTPException(status_code=500, detail="Error interno al actualizar perfil. Intente nuevamente o contacte al administrador.")


@router.delete("/{profile_id}", status_code=204, dependencies=[Depends(check_permission("settings:edit"))])
def delete_profile(
    profile_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("settings:edit"))
):
    """
    Elimina un perfil del sistema.
    
    ADVERTENCIA: Esta operación eliminará en cascada todos los productos y órdenes 
    asociados al perfil debido a las reglas CASCADE configuradas.
    
    Args:
        - profile_id: ID del perfil a eliminar
        
    Returns:
        No content (204)
        
    Raises:
        - 404: Si el perfil no existe
        - 500: Si ocurre un error al eliminar
    """
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"El perfil con ID {profile_id} no fue encontrado"
        )
    
    try:
        db.delete(profile)
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el perfil porque tiene registros relacionados."
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error deleting profile")
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al eliminar perfil."
        )
    except Exception as e:
        db.rollback()
        logger.exception("Error al eliminar perfil")
        raise HTTPException(status_code=500, detail="Error interno al eliminar perfil. Intente nuevamente o contacte al administrador.")
