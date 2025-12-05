from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Profile
from app.schemas import ProfileCreate, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

@router.get("", response_model=List[ProfileResponse])
def list_profiles(db: Session = Depends(get_db)):
    """
    Lista todos los perfiles activos del sistema.
    
    Returns:
        Lista de perfiles activos
    """
    profiles = db.query(Profile).filter(Profile.active == True).all()
    return profiles

@router.post("", response_model=ProfileResponse, status_code=201)
def create_profile(profile: ProfileCreate, db: Session = Depends(get_db)):
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear perfil: {str(e)}")

@router.get("/{profile_id}", response_model=ProfileResponse)
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


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(profile_id: int, updates: ProfileUpdate, db: Session = Depends(get_db)):
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

    if updates.name is not None:
        profile.name = updates.name
    if updates.active is not None:
        profile.active = updates.active

    try:
        db.commit()
        db.refresh(profile)
        return profile
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar perfil: {str(e)}")


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar perfil: {str(e)}")
