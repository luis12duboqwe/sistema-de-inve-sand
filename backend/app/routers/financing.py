from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Bank, FinancingOption
from app.schemas import (
    BankCreate, 
    BankUpdate, 
    BankResponse, 
    FinancingOptionCreate, 
    FinancingOptionResponse
)

router = APIRouter(prefix="/api/financing", tags=["financing"])

@router.get("/banks", response_model=List[BankResponse])
def list_banks(active_only: bool = False, db: Session = Depends(get_db)):
    """Lista todos los bancos y sus opciones de financiamiento"""
    query = db.query(Bank)
    if active_only:
        query = query.filter(Bank.active == True)
    
    banks = query.all()
    return banks

@router.post("/banks", response_model=BankResponse)
def create_bank(bank: BankCreate, db: Session = Depends(get_db)):
    """Crea un nuevo banco"""
    existing = db.query(Bank).filter(Bank.name == bank.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"El banco '{bank.name}' ya existe")
    
    new_bank = Bank(
        name=bank.name, 
        active=bank.active,
        normal_card_rate=bank.normal_card_rate
    )
    db.add(new_bank)
    db.flush()
    
    if bank.financing_options:
        for opt in bank.financing_options:
            new_opt = FinancingOption(
                bank_id=new_bank.id,
                months=opt.months,
                rate=opt.rate,
                active=opt.active
            )
            db.add(new_opt)
    
    db.commit()
    db.refresh(new_bank)
    return new_bank

@router.put("/banks/{bank_id}", response_model=BankResponse)
def update_bank(bank_id: int, bank_update: BankUpdate, db: Session = Depends(get_db)):
    """Actualiza un banco"""
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    
    if bank_update.name is not None:
        bank.name = bank_update.name
    if bank_update.active is not None:
        bank.active = bank_update.active
    if bank_update.normal_card_rate is not None:
        bank.normal_card_rate = bank_update.normal_card_rate
        
    db.commit()
    db.refresh(bank)
    return bank

@router.post("/options", response_model=FinancingOptionResponse)
def create_option(option: FinancingOptionCreate, bank_id: int = Query(..., description="ID del banco"), db: Session = Depends(get_db)):
    """Agrega una opción de financiamiento a un banco"""
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
        
    new_opt = FinancingOption(
        bank_id=bank_id,
        months=option.months,
        rate=option.rate,
        active=option.active
    )
    db.add(new_opt)
    db.commit()
    db.refresh(new_opt)
    return new_opt

@router.delete("/options/{option_id}")
def delete_option(option_id: int, db: Session = Depends(get_db)):
    """Elimina una opción de financiamiento"""
    opt = db.query(FinancingOption).filter(FinancingOption.id == option_id).first()
    if not opt:
        raise HTTPException(status_code=404, detail="Opción no encontrada")
        
    db.delete(opt)
    db.commit()
    return {"message": "Opción eliminada"}
