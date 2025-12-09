from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
import math
from app.database import get_db
from app.models import Product, Profile, Stock, Location, Supplier
from app.schemas import (
    ProductCreate, ProductResponse, ProductUpdate, StockUpdate, 
    CategoriaEnum, PaginatedResponse, StockByLocationResponse, LocationResponse
)

router = APIRouter(prefix="/api/products", tags=["products"])


def _serialize_product(product: Product) -> ProductResponse:
    """
    Helper function to serialize a Product model to ProductResponse schema.
    
    Args:
        - product: Product model instance
        
    Returns:
        ProductResponse with stock_disponible (sum of all locations) and imeis
    """
    # Obtener IMEIs del producto (solo no vendidos)
    imeis_list = []
    if hasattr(product, 'imeis') and product.imeis:
        imeis_list = [imei_obj.imei for imei_obj in product.imeis if not imei_obj.vendido]
    
    # Calcular stock total de todas las ubicaciones
    total_stock = 0
    if hasattr(product, 'stock_items') and product.stock_items:
        total_stock = sum(stock.cantidad_disponible for stock in product.stock_items)
    elif hasattr(product, 'stock') and product.stock:
        # Compatibilidad con modelo antiguo
        total_stock = product.stock.cantidad_disponible if product.stock else 0
    
    return ProductResponse(
        id=product.id,
        profile_id=product.profile_id,
        supplier_id=product.supplier_id,
        sku=product.sku,
        nombre=product.nombre,
        categoria=product.categoria,
        marca=product.marca,
        modelo=product.modelo,
        capacidad=product.capacidad,
        condicion=product.condicion,
        precio=product.precio,
        moneda=product.moneda,
        garantia_meses=product.garantia_meses,
        garantia_condiciones=product.garantia_condiciones,
        activo=product.activo,
        imei=imeis_list[0] if imeis_list else None,  # Primer IMEI por compatibilidad
        imeis=imeis_list if imeis_list else None,
        stock_disponible=total_stock
    )

@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    search: Optional[str] = Query(None, description="Buscar por nombre, marca o modelo"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación con stock disponible"),
    include_inactive: bool = Query(False, description="Incluir productos inactivos y sin stock"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    """
    Lista productos con paginación y filtros V2.0.
    
    V2.0: Todos los productos son globales y visibles para todos los canales de venta.
    El stock se gestiona por ubicación física, no por perfil de negocio.
    
    Filtros disponibles:
    - search: Busca en nombre, marca y modelo
    - location_id: Muestra solo productos con stock en esa ubicación
    - include_inactive: Incluye productos inactivos y sin stock
    
    Siempre incluye el campo `stock_disponible` calculado desde la tabla stock.
    
    Args:
        - search: Término de búsqueda opcional (busca en nombre, marca y modelo)
        - location_id: Filtrar solo productos con stock en esta ubicación
        - include_inactive: Incluir productos inactivos y sin stock
        - page: Número de página (default: 1)
        - per_page: Resultados por página (default: 50, max: 100)
    
    Returns:
        Respuesta paginada con lista de productos
    """
    # V2.0: incluir productos aunque no tengan stock (join externo) y agrupar por producto
    query = db.query(Product).outerjoin(Stock).group_by(Product.id)

    # Filtro por ubicación específica (V2.0)
    if location_id:
        query = query.filter(
            Stock.location_id == location_id,
            Stock.cantidad_disponible > 0
        )
    
    if not include_inactive:
        query = query.filter(
            Product.activo == True,
            or_(Stock.cantidad_disponible.is_(None), Stock.cantidad_disponible > 0)
        )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Product.nombre.ilike(search_term),
                Product.marca.ilike(search_term),
                Product.modelo.ilike(search_term)
            )
        )
    
    total = query.count()
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()
    
    return PaginatedResponse(
        items=[_serialize_product(product) for product in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )

@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo producto con stock inicial.
    
    V2.0: Los productos son globales. profile_id es opcional (solo para compatibilidad V1).
    
    Args:
        - product: Datos del producto a crear
        
    Returns:
        Producto creado con stock_disponible
        
    Raises:
        - 404: Si el profile_id existe y no se encuentra
        - 400: Si el SKU ya existe en la base de datos
    """
    # V2.0: Validar profile_id solo si se proporciona
    if product.profile_id is not None:
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
        
        # V2.0: Extraer initial_location_id y imeis_con_ubicacion
        initial_location_id = product_data.pop("initial_location_id", None)
        imeis_con_ubicacion = product_data.pop("imeis_con_ubicacion", None)
        
        # Extraer IMEIs legacy si existen
        imeis = product_data.pop("imeis", None)
        
        # Eliminar el campo imei obsoleto (usar imeis en su lugar)
        product_data.pop("imei", None)
        
        db_product = Product(**product_data)
        db.add(db_product)
        db.flush()
        
        # V2.0: Crear registro de stock por ubicación
        if cantidad_inicial > 0:
            if not initial_location_id:
                # Si no se especifica ubicación, buscar la primera tienda activa
                default_location = db.query(Location).filter(
                    Location.tipo == "tienda",
                    Location.activo == True
                ).first()
                
                if not default_location:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail="Debe especificar initial_location_id o tener al menos una tienda activa"
                    )
                initial_location_id = default_location.id
            else:
                # Validar que la ubicación exista
                location = db.query(Location).filter(Location.id == initial_location_id).first()
                if not location:
                    db.rollback()
                    raise HTTPException(
                        status_code=404,
                        detail=f"Ubicación con ID {initial_location_id} no encontrada"
                    )
            
            db_stock = Stock(
                product_id=db_product.id,
                location_id=initial_location_id,
                cantidad_disponible=cantidad_inicial
            )
            db.add(db_stock)
            
            # TRAZABILIDAD: Registrar en historial de stock
            from app.models import StockHistory
            stock_history = StockHistory(
                product_id=db_product.id,
                location_id=initial_location_id,
                tipo_cambio='ajuste',  # Creación inicial del producto
                cantidad=cantidad_inicial,
                stock_anterior=0,
                stock_nuevo=cantidad_inicial,
                referencia_id=db_product.id,
                referencia_tipo='product_creation',
                notas=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                usuario='sistema'
            )
            db.add(stock_history)
        
        # V2.0: Procesar IMEIs con ubicación
        if imeis_con_ubicacion and len(imeis_con_ubicacion) > 0:
            from app.models import ProductIMEI
            
            # VALIDACIÓN: Cantidad de IMEIs debe coincidir con stock inicial
            if cantidad_inicial > 0 and len(imeis_con_ubicacion) != cantidad_inicial:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"La cantidad de IMEIs ({len(imeis_con_ubicacion)}) debe coincidir con el stock inicial ({cantidad_inicial})"
                )
            
            for imei_data in imeis_con_ubicacion:
                # VALIDACIÓN: IMEIs deben estar en la misma ubicación que el stock inicial
                if initial_location_id and imei_data.location_id != initial_location_id:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Todos los IMEIs deben estar en la ubicación inicial (location_id={initial_location_id}). IMEI '{imei_data.imei}' está en ubicación {imei_data.location_id}"
                    )
                
                # Validar que la ubicación existe y está activa
                location = db.query(Location).filter(
                    Location.id == imei_data.location_id,
                    Location.activo == True
                ).first()
                if not location:
                    db.rollback()
                    raise HTTPException(
                        status_code=404,
                        detail=f"Ubicación con ID {imei_data.location_id} no encontrada o inactiva para IMEI {imei_data.imei}"
                    )
                
                # Verificar que el IMEI no exista
                existing_imei = db.query(ProductIMEI).filter(
                    ProductIMEI.imei == imei_data.imei.strip()
                ).first()
                if existing_imei:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"El IMEI '{imei_data.imei.strip()}' ya está registrado"
                    )
                
                db_imei = ProductIMEI(
                    product_id=db_product.id,
                    location_id=imei_data.location_id,
                    imei=imei_data.imei.strip(),
                    vendido=False
                )
                db.add(db_imei)
        
        # LEGACY: Si hay IMEIs sin ubicación (para compatibilidad V1)
        elif imeis and len(imeis) > 0:
            from app.models import ProductIMEI
            for imei_value in imeis:
                if imei_value and imei_value.strip():
                    # Verificar que el IMEI no exista
                    existing_imei = db.query(ProductIMEI).filter(ProductIMEI.imei == imei_value.strip()).first()
                    if existing_imei:
                        db.rollback()
                        raise HTTPException(
                            status_code=400,
                            detail=f"El IMEI '{imei_value.strip()}' ya está registrado en otro producto"
                        )
                    
                    db_imei = ProductIMEI(
                        product_id=db_product.id,
                        location_id=initial_location_id if initial_location_id else None,  # Asignar a ubicación inicial si existe
                        imei=imei_value.strip(),
                        vendido=False
                    )
                    db.add(db_imei)
        
        db.commit()
        db.refresh(db_product)
        
        return _serialize_product(db_product)
    except HTTPException:
        raise
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


@router.get("/{product_id}/stock/by-location", response_model=PaginatedResponse[StockByLocationResponse])
def get_product_stock_by_location(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el desglose de stock de un producto por ubicación (V2.0).
    
    Retorna una lista de todas las ubicaciones donde el producto tiene stock,
    incluyendo información de cada ubicación.
    
    Args:
        product_id: ID del producto
        
    Returns:
        Lista paginada de stock por ubicación con detalles de cada ubicación
        
    Raises:
        404: Si el producto no existe
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    # Obtener todos los registros de stock para este producto
    stock_items = db.query(Stock).filter(
        Stock.product_id == product_id
    ).join(Location).filter(Location.activo == True).all()
    
    # Serializar con información de ubicación
    from app.schemas import StockByLocationResponse, LocationResponse
    
    items = []
    for stock_item in stock_items:
        items.append(StockByLocationResponse(
            id=stock_item.id,
            product_id=stock_item.product_id,
            location_id=stock_item.location_id,
            cantidad_disponible=stock_item.cantidad_disponible,
            location=LocationResponse(
                id=stock_item.location.id,
                nombre=stock_item.location.nombre,
                tipo=stock_item.location.tipo,
                direccion=stock_item.location.direccion,
                telefono=stock_item.location.telefono,
                activo=stock_item.location.activo,
                created_at=stock_item.location.created_at,
                updated_at=stock_item.location.updated_at
            ) if stock_item.location else None
        ))
    
    return PaginatedResponse(
        items=items,
        total=len(items),
        page=1,
        per_page=len(items),
        pages=1
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, updates: ProductUpdate, db: Session = Depends(get_db)):
    """
    Actualiza un producto existente y devuelve su stock actual.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"El producto con ID {product_id} no fue encontrado")

    # Validar SKU único si se está actualizando
    if updates.sku is not None and updates.sku != product.sku:
        existing_sku = db.query(Product).filter(
            Product.sku == updates.sku,
            Product.id != product_id
        ).first()
        if existing_sku:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe otro producto con el SKU '{updates.sku}'"
            )
        product.sku = updates.sku

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
        nuevo_precio = Decimal(updates.precio)
        if nuevo_precio <= 0:
            raise HTTPException(
                status_code=400,
                detail="El precio debe ser mayor a 0"
            )
        product.precio = nuevo_precio
    if updates.moneda is not None:
        product.moneda = updates.moneda
    if updates.garantia_meses is not None:
        if updates.garantia_meses < 0:
            raise HTTPException(
                status_code=400,
                detail="La garantía en meses no puede ser negativa"
            )
        product.garantia_meses = updates.garantia_meses
    if updates.garantia_condiciones is not None:
        product.garantia_condiciones = updates.garantia_condiciones
    if updates.supplier_id is not None:
        # Validar que el supplier existe si se proporciona
        if updates.supplier_id > 0:
            supplier = db.query(Supplier).filter(Supplier.id == updates.supplier_id).first()
            if not supplier:
                raise HTTPException(
                    status_code=404,
                    detail=f"El proveedor con ID {updates.supplier_id} no fue encontrado"
                )
        product.supplier_id = updates.supplier_id
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
def update_product_stock(
    product_id: int, 
    update: StockUpdate, 
    location_id: int = Query(..., description="ID de la ubicación donde actualizar el stock"),
    db: Session = Depends(get_db)
):
    """
    Actualiza la cantidad disponible de stock para un producto en una ubicación específica.
    
    V2.0: Requiere location_id porque el stock es por ubicación física.
    
    Args:
        - product_id: ID del producto
        - update: Nueva cantidad de stock
        - location_id: ID de la ubicación donde actualizar el stock
    
    Returns:
        Mensaje de confirmación
        
    Raises:
        - 404: Si no se encuentra stock para ese producto en esa ubicación
    """
    stock = db.query(Stock).filter(
        Stock.product_id == product_id,
        Stock.location_id == location_id
    ).first()
    
    if not stock:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontró stock para el producto {product_id} en la ubicación {location_id}"
        )
    
    # Validar que el nuevo stock no sea negativo
    if update.cantidad_disponible < 0:
        raise HTTPException(
            status_code=400,
            detail=f"El stock no puede ser negativo. Valor proporcionado: {update.cantidad_disponible}"
        )
    
    # Registrar cambio en historial
    from app.models import StockHistory
    stock_anterior = stock.cantidad_disponible
    stock.cantidad_disponible = update.cantidad_disponible
    
    history = StockHistory(
        product_id=product_id,
        location_id=location_id,
        tipo_cambio='ajuste',
        cantidad=update.cantidad_disponible - stock_anterior,
        stock_anterior=stock_anterior,
        stock_nuevo=update.cantidad_disponible,
        referencia_id=None,
        referencia_tipo='manual_adjustment',
        notas=f"Ajuste manual de stock: {stock_anterior} → {update.cantidad_disponible}",
        usuario='sistema'  # TODO: Usar usuario autenticado
    )
    db.add(history)

    try:
        db.commit()
        return {"message": "Stock actualizado", "stock_anterior": float(stock_anterior), "stock_nuevo": update.cantidad_disponible}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar stock: {str(e)}")


@router.post("/bulk", response_model=List[ProductResponse], status_code=201)
def bulk_create_products(payload: dict, db: Session = Depends(get_db)):
    """
    Crea múltiples productos en una sola operación.
    
    V2.0: Los productos son globales y el stock debe asignarse por ubicación.
    Si no se envía initial_location_id, se usará la primera tienda activa.
    """
    products_data = payload.get("products", [])
    if not isinstance(products_data, list) or len(products_data) == 0:
        raise HTTPException(status_code=400, detail="Se requiere una lista de productos")

    created_products = []

    try:
        # Ubicación por defecto si no se envía initial_location_id
        default_location = db.query(Location).filter(
            Location.tipo == "tienda",
            Location.activo == True
        ).first()

        for product_input in products_data:
            product = ProductCreate.model_validate(product_input)

            # V2.0: profile_id es opcional
            if product.profile_id is not None:
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
            initial_location_id = product_data.pop("initial_location_id", None)
            product_data.pop("imeis_con_ubicacion", None)  # No soportado en bulk

            # Determinar ubicación destino
            location = None
            if initial_location_id:
                location = db.query(Location).filter(
                    Location.id == initial_location_id,
                    Location.activo == True
                ).first()
                if not location:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Ubicación con ID {initial_location_id} no encontrada o inactiva"
                    )
            else:
                location = default_location

            if not location:
                raise HTTPException(
                    status_code=400,
                    detail="Debe especificar initial_location_id o tener al menos una tienda activa para carga masiva"
                )

            db_product = Product(**product_data)
            db.add(db_product)
            db.flush()

            # Crear stock en ubicación definida
            if cantidad_inicial < 0:
                raise HTTPException(status_code=400, detail="stock_inicial no puede ser negativo")

            db_stock = Stock(
                product_id=db_product.id,
                location_id=location.id,
                cantidad_disponible=cantidad_inicial
            )
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
    
    # Verificar si el producto está en alguna orden activa (pendiente o por entregar)
    from app.models import OrderItem, Order
    active_order_items = db.query(OrderItem).join(Order).filter(
        OrderItem.product_id == product_id,
        Order.estado.in_(['pendiente', 'por_entregar'])
    ).count()
    
    if active_order_items > 0:
        # Obtener información de las órdenes activas
        active_order_ids = db.query(Order.id, Order.estado).join(OrderItem).filter(
            OrderItem.product_id == product_id,
            Order.estado.in_(['pendiente', 'por_entregar'])
        ).distinct().all()
        order_info = [f"#{oid} ({estado})" for oid, estado in active_order_ids]
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el producto porque está en {active_order_items} orden(es) activa(s): {', '.join(order_info)}. Desactívelo usando 'activo=false'."
        )
    
    # Verificar si está en órdenes históricas (completadas/canceladas)
    historical_order_items = db.query(OrderItem).join(Order).filter(
        OrderItem.product_id == product_id,
        Order.estado.in_(['completada', 'cancelada'])
    ).count()
    
    if historical_order_items > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el producto porque está referenciado en {historical_order_items} órdenes históricas. Use 'activo=false' para desactivarlo sin perder trazabilidad."
        )
    
    try:
        # V2.0: Eliminar IMEIs asociados primero
        from app.models import ProductIMEI
        imeis = db.query(ProductIMEI).filter(ProductIMEI.product_id == product_id).all()
        for imei in imeis:
            db.delete(imei)
        
        # Eliminar el stock asociado primero
        if product.stock:
            db.delete(product.stock)
        # Eliminar todos los stocks por ubicación
        if hasattr(product, 'stock_items') and product.stock_items:
            for stock_item in product.stock_items:
                db.delete(stock_item)
        # Luego eliminar el producto
        db.delete(product)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar producto: {str(e)}")


# ============= NUEVOS ENDPOINTS PARA STOCK POR UBICACIÓN =============

@router.get("/{product_id}/stock/by-location")
def get_product_stock_by_location(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener el stock de un producto desglosado por ubicación.
    
    Retorna:
    - Stock en cada ubicación
    - Stock total consolidado
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    stock_by_location = db.query(Stock, Location).join(
        Location, Stock.location_id == Location.id
    ).filter(Stock.product_id == product_id).all()
    
    locations_data = []
    total_stock = 0
    
    for stock, location in stock_by_location:
        locations_data.append({
            "location_id": location.id,
            "location_name": location.nombre,
            "location_type": location.tipo,
            "cantidad": stock.cantidad_disponible
        })
        total_stock += stock.cantidad_disponible
    
    return {
        "product_id": product_id,
        "product_name": product.nombre,
        "sku": product.sku,
        "locations": locations_data,
        "total_stock": total_stock
    }


@router.post("/{product_id}/stock/location/{location_id}")
def set_product_stock_at_location(
    product_id: int,
    location_id: int,
    cantidad: int = Query(..., ge=0, description="Cantidad de stock en esta ubicación"),
    db: Session = Depends(get_db)
):
    """
    Establecer o actualizar el stock de un producto en una ubicación específica.
    """
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Verificar que la ubicación existe
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    
    # Buscar o crear el registro de stock
    stock = db.query(Stock).filter(
        Stock.product_id == product_id,
        Stock.location_id == location_id
    ).first()
    
    stock_anterior = stock.cantidad_disponible if stock else 0
    
    if stock:
        stock.cantidad_disponible = cantidad
    else:
        stock = Stock(
            product_id=product_id,
            location_id=location_id,
            cantidad_disponible=cantidad
        )
        db.add(stock)
    
    db.commit()
    db.refresh(stock)
    
    # Registrar en historial de stock
    from app.models import StockHistory
    # Determinar tipo de cambio según la operación
    if cantidad > stock_anterior:
        tipo_cambio = "ajuste"  # Incremento
        cantidad_cambio = cantidad - stock_anterior
    elif cantidad < stock_anterior:
        tipo_cambio = "ajuste"  # Decremento
        cantidad_cambio = stock_anterior - cantidad  # Siempre positivo para decrementos en este endpoint
    else:
        tipo_cambio = "ajuste"  # Sin cambio real
        cantidad_cambio = 0
    
    stock_history = StockHistory(
        product_id=product_id,
        location_id=location_id,
        tipo_cambio=tipo_cambio,
        cantidad=cantidad_cambio if cantidad > stock_anterior else -cantidad_cambio,  # Positivo=entrada, Negativo=salida
        stock_anterior=stock_anterior,
        stock_nuevo=cantidad,
        referencia_tipo="manual_adjustment",
        notas="Ajuste manual de stock",
        usuario="Sistema"
    )
    db.add(stock_history)
    db.commit()
    
    return {
        "product_id": product_id,
        "location_id": location_id,
        "location_name": location.nombre,
        "cantidad": stock.cantidad_disponible,
        "message": f"Stock actualizado en {location.nombre}"
    }


@router.get("/{product_id}/stock/total")
def get_product_total_stock(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener el stock total de un producto sumando todas las ubicaciones.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    total = db.query(func.sum(Stock.cantidad_disponible)).filter(
        Stock.product_id == product_id
    ).scalar() or 0
    
    return {
        "product_id": product_id,
        "product_name": product.nombre,
        "sku": product.sku,
        "total_stock": int(total)
    }
