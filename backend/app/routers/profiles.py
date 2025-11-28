from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Profile
from app.schemas import ProfileCreate, ProfileResponse

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

@router.get("", response_model=List[ProfileResponse])
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(Profile).filter(Profile.active == True).all()
    return profiles

@router.post("", response_model=ProfileResponse, status_code=201)
def create_profile(profile: ProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(Profile).filter(Profile.slug == profile.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="El slug ya existe")
    
    db_profile = Profile(**profile.model_dump())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return profile
