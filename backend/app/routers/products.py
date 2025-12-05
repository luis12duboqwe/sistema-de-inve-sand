from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.database import get_db
from app.models import Product, Profile, Stock
from app.schemas import ProductCreate, ProductResponse, ProductUpdate, StockUpdate, CategoriaEnum

router = APIRouter(prefix="/api/products", tags=["products"])


def _serialize_product(product: Product) -> ProductResponse:
    """
    Helper function to serialize a Product model to ProductResponse schema.
    
    Args:
        - product: Product model instance
        
    Returns:
        ProductResponse with stock_disponible
    """
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

@router.get("", response_model=List[ProductResponse])
def list_products(
    profile_slug: Optional[str] = Query(None, description="Filtrar por slug del perfil (ej: 'softmobile')"),
    search: Optional[str] = Query(None, description="Buscar por nombre, marca o modelo"),
    include_inactive: bool = Query(False, description="Incluir productos inactivos y sin stock"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los productos activos con stock disponible.
    
    Siempre incluye el campo `stock_disponible` calculado desde la tabla stock.
    
    Args:
        - profile_slug: Filtro opcional por perfil
        - search: Término de búsqueda opcional (busca en nombre, marca y modelo)
    
    Returns:
        Lista de productos con stock disponible
        
    Raises:
        - 404: Si el profile_slug especificado no existe
    """
    query = db.query(Product).join(Stock)

    if not include_inactive:
        query = query.filter(
            Product.activo == True,
            Stock.cantidad_disponible > 0
        )
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404, 
                detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
            )
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
    
    return [_serialize_product(product) for product in products]

@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo producto con stock inicial.
    
    Args:
        - product: Datos del producto a crear
        
    Returns:
        Producto creado con stock_disponible
        
    Raises:
        - 404: Si el profile_id no existe
        - 400: Si el SKU ya existe en la base de datos
    """
    profile = db.query(Profile).filter(Profile.id == product.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=404, 
            detail=f"El perfil con ID {product.profile_id} no fue encontrado"
        )
    
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un producto con el SKU '{product.sku}'"
        )
    
    if product.categoria == CategoriaEnum.CELULAR and product.garantia_meses == 0:
        product.garantia_meses = 2
    
    try:
        product_data = product.model_dump(by_alias=True)
        cantidad_inicial = product_data.pop("stock_inicial", product_data.pop("cantidad_inicial", 0))
        
        db_product = Product(**product_data)
        db.add(db_product)
        db.flush()
        
        db_stock = Stock(product_id=db_product.id, cantidad_disponible=cantidad_inicial)
        db.add(db_stock)
        
        db.commit()
        db.refresh(db_product)
        
        return _serialize_product(db_product)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear producto: {str(e)}")

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un producto por su ID.
    
    Incluye el campo stock_disponible calculado desde la tabla stock.
    
    Args:
        - product_id: ID del producto
        
    Returns:
        Producto con stock_disponible
        
    Raises:
        - 404: Si el producto no existe
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"El producto con ID {product_id} no fue encontrado"
        )
    
    return _serialize_product(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, updates: ProductUpdate, db: Session = Depends(get_db)):
    """
    Actualiza un producto existente y devuelve su stock actual.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"El producto con ID {product_id} no fue encontrado")

    if updates.nombre is not None:
        product.nombre = updates.nombre
    if updates.categoria is not None:
        product.categoria = updates.categoria
    if updates.marca is not None:
        product.marca = updates.marca
    if updates.modelo is not None:
        product.modelo = updates.modelo
    if updates.capacidad is not None:
        product.capacidad = updates.capacidad
    if updates.condicion is not None:
        product.condicion = updates.condicion
    if updates.precio is not None:
        product.precio = Decimal(updates.precio)
    if updates.moneda is not None:
        product.moneda = updates.moneda
    if updates.garantia_meses is not None:
        product.garantia_meses = updates.garantia_meses
    if updates.activo is not None:
        product.activo = updates.activo

    try:
        db.commit()
        db.refresh(product)
        return _serialize_product(product)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar producto: {str(e)}")


@router.put("/{product_id}/stock")
def update_product_stock(product_id: int, update: StockUpdate, db: Session = Depends(get_db)):
    """
    Actualiza la cantidad disponible de stock para un producto.
    """
    stock = db.query(Stock).filter(Stock.product_id == product_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"No se encontró stock para el producto {product_id}")

    stock.cantidad_disponible = update.cantidad_disponible

    try:
        db.commit()
        return {"message": "Stock actualizado"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar stock: {str(e)}")


@router.post("/bulk", response_model=List[ProductResponse], status_code=201)
def bulk_create_products(payload: dict, db: Session = Depends(get_db)):
    """
    Crea múltiples productos en una sola operación.
    """
    products_data = payload.get("products", [])
    if not isinstance(products_data, list) or len(products_data) == 0:
        raise HTTPException(status_code=400, detail="Se requiere una lista de productos")

    created_products = []

    try:
        for product_input in products_data:
            product = ProductCreate.model_validate(product_input)

            profile = db.query(Profile).filter(Profile.id == product.profile_id).first()
            if not profile:
                raise HTTPException(
                    status_code=404,
                    detail=f"El perfil con ID {product.profile_id} no fue encontrado"
                )

            existing = db.query(Product).filter(Product.sku == product.sku).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe un producto con el SKU '{product.sku}'"
                )

            product_data = product.model_dump(by_alias=True)
            cantidad_inicial = product_data.pop("stock_inicial", product_data.pop("cantidad_inicial", 0))

            db_product = Product(**product_data)
            db.add(db_product)
            db.flush()

            db_stock = Stock(product_id=db_product.id, cantidad_disponible=cantidad_inicial)
            db.add(db_stock)

            created_products.append((db_product, db_stock))

        db.commit()

        return [_serialize_product(product) for product, _ in created_products]
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear productos: {str(e)}")


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Elimina un producto del sistema.
    
    NOTA: Si el producto está referenciado en order_items, la eliminación 
    fallará debido a la restricción RESTRICT en la foreign key.
    
    Args:
        - product_id: ID del producto a eliminar
        
    Returns:
        No content (204)
        
    Raises:
        - 404: Si el producto no existe
        - 400: Si el producto está referenciado en órdenes
        - 500: Si ocurre un error al eliminar
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"El producto con ID {product_id} no fue encontrado"
        )
    
    try:
        db.delete(product)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        # Check if it's a foreign key constraint error
        error_msg = str(e)
        if "FOREIGN KEY constraint failed" in error_msg or "foreign key" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"No se puede eliminar el producto porque está referenciado en órdenes existentes"
            )
        raise HTTPException(status_code=500, detail=f"Error al eliminar producto: {str(e)}")
