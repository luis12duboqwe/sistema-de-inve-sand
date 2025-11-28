from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.database import get_db
from app.models import Product, Profile, Stock
from app.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=List[ProductResponse])
def list_products(
    profile_slug: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Product).join(Stock).filter(
        Product.activo == True,
        Stock.cantidad_disponible > 0
    )
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")
        query = query.filter(Product.profile_id == profile.id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.nombre.ilike(search_term),
                Product.marca.ilike(search_term),
                Product.modelo.ilike(search_term)
            )
        )
    
    products = query.all()
    
    result = []
    for product in products:
        result.append(ProductResponse(
            id=product.id,
            nombre=product.nombre,
            categoria=product.categoria,
            marca=product.marca,
            modelo=product.modelo,
            capacidad=product.capacidad,
            condicion=product.condicion,
            precio=product.precio,
            moneda=product.moneda,
            garantia_meses=product.garantia_meses,
            stock_disponible=product.stock.cantidad_disponible
        ))
    
    return result

@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == product.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="El SKU ya existe")
    
    if product.categoria == "celular" and product.garantia_meses == 0:
        product.garantia_meses = 2
    
    product_data = product.model_dump()
    cantidad_inicial = product_data.pop("cantidad_inicial", 0)
    
    db_product = Product(**product_data)
    db.add(db_product)
    db.flush()
    
    db_stock = Stock(product_id=db_product.id, cantidad_disponible=cantidad_inicial)
    db.add(db_stock)
    
    db.commit()
    db.refresh(db_product)
    
    return ProductResponse(
        id=db_product.id,
        nombre=db_product.nombre,
        categoria=db_product.categoria,
        marca=db_product.marca,
        modelo=db_product.modelo,
        capacidad=db_product.capacidad,
        condicion=db_product.condicion,
        precio=db_product.precio,
        moneda=db_product.moneda,
        garantia_meses=db_product.garantia_meses,
        stock_disponible=db_stock.cantidad_disponible
    )

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return ProductResponse(
        id=product.id,
        nombre=product.nombre,
        categoria=product.categoria,
        marca=product.marca,
        modelo=product.modelo,
        capacidad=product.capacidad,
        condicion=product.condicion,
        precio=product.precio,
        moneda=product.moneda,
        garantia_meses=product.garantia_meses,
        stock_disponible=product.stock.cantidad_disponible if product.stock else 0
    )
