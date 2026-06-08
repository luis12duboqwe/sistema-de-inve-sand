from datetime import UTC, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import math
from app.database import get_db
from app.models import Product, Profile, Stock, Location, Supplier, ProductIMEI, StockHistory, IMEIHistory, StockTransfer, User
from app.schemas import (
    ProductCreate, ProductResponse, ProductUpdate, ProductRestockRequest, StockUpdate,
    CategoriaEnum, PaginatedResponse, StockByLocationResponse, LocationResponse
)
from app.auth import check_permission, get_current_active_user
from app.utils.location_access import get_accessible_location_ids, require_location_access
from app.utils.audit import log_audit_event

router = APIRouter(prefix="/api/products", tags=["products"])


def _require_active_location_for_stock(db: Session, current_user: User, location_id: int) -> Location:
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=404,
            detail=f"La ubicación con ID {location_id} no fue encontrada",
        )
    if not location.activo:
        raise HTTPException(
            status_code=400,
            detail=f"La ubicación '{location.nombre}' está inactiva. No se puede modificar stock aquí.",
        )
    require_location_access(db, current_user, location_id, "can_edit")
    return location


def _get_default_editable_location(db: Session, current_user: User) -> Optional[Location]:
    query = db.query(Location).filter(
        Location.tipo == "tienda",
        Location.activo == True,
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_edit")
    if accessible_location_ids is not None:
        if not accessible_location_ids:
            return None
        query = query.filter(Location.id.in_(accessible_location_ids))
    return query.first()


def _extract_imei_location(imei_data) -> tuple[str, int]:
    imei_val = imei_data.get("imei") if isinstance(imei_data, dict) else imei_data.imei
    loc_id = imei_data.get("location_id") if isinstance(imei_data, dict) else imei_data.location_id
    return imei_val.strip(), int(loc_id)


def _first_duplicate(values: List[str]) -> Optional[str]:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def _serialize_product(product: Product, accessible_location_ids: Optional[List[int]] = None) -> ProductResponse:
    """
    Helper function to serialize a Product model to ProductResponse schema.
    
    Args:
        - product: Product model instance
        
    Returns:
        ProductResponse with stock_disponible (sum of all locations) and stock_items
    """
    # Obtener IMEIs del producto (solo no vendidos)
    imeis_list = []
    if hasattr(product, 'imeis') and product.imeis:
        imeis_list = [
            imei_obj.imei
            for imei_obj in product.imeis
            if not imei_obj.vendido
            and (accessible_location_ids is None or imei_obj.location_id in accessible_location_ids)
        ]
    
    # Calcular stock total de todas las ubicaciones
    total_stock = 0
    stock_items_list = []
    
    if hasattr(product, 'stock_items') and product.stock_items:
        total_stock = 0
        # Serializar stock_items para V2.0, incluyendo stock libre (descontando reservas)
        for stock_item in product.stock_items:
            if accessible_location_ids is not None and stock_item.location_id not in accessible_location_ids:
                continue
            cantidad_reservada = stock_item.cantidad_reservada or 0
            stock_libre = max((stock_item.cantidad_disponible or 0) - cantidad_reservada, 0)
            total_stock += stock_libre

            stock_items_list.append(StockByLocationResponse(
                id=stock_item.id,
                product_id=stock_item.product_id,
                location_id=stock_item.location_id,
                cantidad_disponible=stock_item.cantidad_disponible,
                cantidad_reservada=cantidad_reservada,
                cantidad_defectuosa=stock_item.cantidad_defectuosa or 0,
                stock_libre=stock_libre,
                location=LocationResponse(
                    id=stock_item.location.id,
                    nombre=stock_item.location.nombre,
                    tipo=stock_item.location.tipo,
                    direccion=stock_item.location.direccion,
                    activo=stock_item.location.activo,
                    created_at=stock_item.location.created_at,
                    updated_at=stock_item.location.updated_at
                ) if stock_item.location else None
            ))
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
        costo=product.costo, # V2.0: Incluir costo para reportes
        moneda=product.moneda,
        garantia_meses=product.garantia_meses,
        garantia_condiciones=product.garantia_condiciones,
        activo=product.activo,
        is_serialized=product.is_serialized, # V2.0: Incluir flag de serialización
        imei=imeis_list[0] if imeis_list else None,  # Primer IMEI por compatibilidad
        imeis=imeis_list if imeis_list else None,
        stock_disponible=total_stock,
        stock_items=stock_items_list if stock_items_list else None
    )


@router.get("/{product_id}/imeis", response_model=List[str], dependencies=[Depends(check_permission("inventory:view"))])
def get_product_imeis(
    product_id: int,
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Obtiene los IMEIs disponibles para un producto, opcionalmente filtrados por ubicación.
    """
    query = db.query(ProductIMEI.imei).filter(
        ProductIMEI.product_id == product_id,
        ProductIMEI.vendido == False,
        ProductIMEI.transfer_id == None,  # No incluir los que están en tránsito
        ProductIMEI.order_id == None,     # No incluir los reservados en órdenes pendientes
    )
    
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")

    if location_id:
        require_location_access(db, current_user, location_id, "can_view")
        query = query.filter(ProductIMEI.location_id == location_id)
    elif accessible_location_ids is not None:
        query = query.filter(ProductIMEI.location_id.in_(accessible_location_ids))
        
    imeis = query.all()
    return [i.imei for i in imeis]


@router.get("/imei/{imei}", response_model=ProductResponse, dependencies=[Depends(check_permission("inventory:view"))])
def get_product_by_imei(
    imei: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Busca un producto por su IMEI.
    Útil para escaneo de códigos de barras en fulfillment.
    """
    product_imei = db.query(ProductIMEI).filter(ProductIMEI.imei == imei).first()
    if not product_imei:
        raise HTTPException(status_code=404, detail=f"IMEI {imei} no encontrado")
    if product_imei.location_id:
        require_location_access(db, current_user, product_imei.location_id, "can_view")
    
    product = db.query(Product).filter(Product.id == product_imei.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto asociado al IMEI no encontrado")
        
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    return _serialize_product(product, accessible_location_ids)


@router.get("", response_model=PaginatedResponse[ProductResponse], dependencies=[Depends(check_permission("inventory:view"))])
def list_products(
    search: Optional[str] = Query(None, description="Buscar por nombre, marca o modelo"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación con stock disponible"),
    include_inactive: bool = Query(False, description="Incluir productos inactivos y sin stock"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    # V2.0: Eager loading de stock_items y location para incluir en response
    # 🔒 BUG #27 FIX: Separar joinedload (para datos) del join (para filtros)
    query = db.query(Product).options(
        joinedload(Product.stock_items).joinedload(Stock.location)
    )
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")

    if accessible_location_ids == []:
        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=0,
        )

    # Filtro por ubicación específica (V2.0) - SEPARADO del joinedload
    if location_id:
        if accessible_location_ids is not None and location_id not in accessible_location_ids:
            raise HTTPException(status_code=403, detail="No tiene acceso a esta ubicación")
        # Usar distinct() para evitar cartesian product con joinedload
        stock_filters = [Stock.location_id == location_id]
        if not include_inactive:
            stock_filters.append(Stock.cantidad_disponible > 0)
        query = query.join(Stock, Product.id == Stock.product_id).filter(*stock_filters).distinct()
    elif accessible_location_ids is not None:
        stock_filters = [Stock.location_id.in_(accessible_location_ids)]
        if not include_inactive:
            stock_filters.append(Stock.cantidad_disponible > 0)
        query = query.join(Stock, Product.id == Stock.product_id).filter(*stock_filters).distinct()
    
    if not include_inactive:
        query = query.filter(Product.activo == True)
    
    if search:
        # V2.1: Búsqueda inteligente por palabras clave (AND implícito)
        # Permite encontrar "iPhone 13" buscando "13 iPhone" o "iPhone Pro"
        keywords = search.split()
        if keywords:
            and_conditions = []
            for k in keywords:
                term = f"%{k}%"
                and_conditions.append(
                    or_(
                        Product.nombre.ilike(term),
                        Product.marca.ilike(term),
                        Product.modelo.ilike(term),
                        Product.sku.ilike(term)
                    )
                )
            query = query.filter(*and_conditions)
    
    total = query.count()
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()
    
    return PaginatedResponse(
        items=[_serialize_product(product, accessible_location_ids) for product in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0
    )

@router.post("", response_model=ProductResponse, status_code=201, dependencies=[Depends(check_permission("inventory:create"))])
def create_product(
    product: ProductCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
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
        
        # VALIDACIÓN: Enforce IMEIs for serialized products if stock > 0
        # Si es celular, forzar is_serialized a True si no se especificó lo contrario
        if product.categoria == CategoriaEnum.CELULAR and not product.is_serialized:
             product.is_serialized = True
             product_data['is_serialized'] = True

        if product.is_serialized and cantidad_inicial > 0:
            has_imeis = (imeis_con_ubicacion and len(imeis_con_ubicacion) > 0) or (product.imeis and len(product.imeis) > 0)
            if not has_imeis:
                raise HTTPException(
                    status_code=400,
                    detail="Para productos serializados con stock inicial, debe proporcionar los IMEIs."
                )
        
        if initial_location_id:
            _require_active_location_for_stock(db, current_user, initial_location_id)
        
        # Extraer IMEIs legacy si existen
        imeis = product_data.pop("imeis", None)
        
        # Eliminar el campo imei obsoleto (usar imeis en su lugar)
        product_data.pop("imei", None)

        imeis_a_validar: List[str] = []
        if imeis_con_ubicacion:
            for imei_data in imeis_con_ubicacion:
                imei_val, _loc_id = _extract_imei_location(imei_data)
                if imei_val:
                    imeis_a_validar.append(imei_val)
        elif imeis:
            imeis_a_validar = [
                str(imei_value).strip()
                for imei_value in imeis
                if imei_value and str(imei_value).strip()
            ]

        duplicate_imei = _first_duplicate(imeis_a_validar)
        if duplicate_imei:
            raise HTTPException(
                status_code=400,
                detail=f"El IMEI '{duplicate_imei}' está duplicado en esta carga. Revise los campos antes de guardar."
            )

        if imeis_a_validar:
            existing_imei = db.query(ProductIMEI).filter(ProductIMEI.imei.in_(imeis_a_validar)).first()
            if existing_imei:
                raise HTTPException(
                    status_code=400,
                    detail=f"El IMEI '{existing_imei.imei}' ya está registrado en el sistema"
                )
        
        db_product = Product(**product_data)
        db.add(db_product)
        db.flush()
        
        # V2.0: Crear registro de stock por ubicación
        if cantidad_inicial > 0:
            if not initial_location_id:
                # Si no se especifica ubicación, buscar la primera tienda activa
                default_location = _get_default_editable_location(db, current_user)
                
                if not default_location:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail="Debe especificar initial_location_id o tener al menos una tienda activa"
                    )
                initial_location_id = default_location.id
            else:
                _require_active_location_for_stock(db, current_user, initial_location_id)
            
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
                usuario=current_user.username
            )
            db.add(stock_history)
        
        # V2.0: Procesar IMEIs con ubicación
        if imeis_con_ubicacion and len(imeis_con_ubicacion) > 0:
            # ProductIMEI ya está importado globalmente
            
            # VALIDACIÓN: Cantidad de IMEIs debe coincidir con stock inicial
            if cantidad_inicial > 0 and len(imeis_con_ubicacion) != cantidad_inicial:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"La cantidad de IMEIs ({len(imeis_con_ubicacion)}) debe coincidir con el stock inicial ({cantidad_inicial})"
                )
            
            for imei_data in imeis_con_ubicacion:
                # Convertir a dict si es necesario (aunque Pydantic debería manejarlo)
                # El error 'dict object has no attribute location_id' sugiere que imei_data es un dict
                # pero estamos intentando acceder como objeto.
                
                imei_val, loc_id = _extract_imei_location(imei_data)

                # VALIDACIÓN: IMEIs deben estar en la misma ubicación que el stock inicial
                if initial_location_id and loc_id != initial_location_id:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Todos los IMEIs deben estar en la ubicación inicial (location_id={initial_location_id}). IMEI '{imei_val}' está en ubicación {loc_id}"
                    )
                
                _require_active_location_for_stock(db, current_user, loc_id)
                
                # Verificar que el IMEI no exista
                existing_imei = db.query(ProductIMEI).filter(
                    ProductIMEI.imei == imei_val.strip()
                ).first()
                if existing_imei:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"El IMEI '{imei_val.strip()}' ya está registrado"
                    )
                
                db_imei = ProductIMEI(
                    product_id=db_product.id,
                    location_id=loc_id,
                    supplier_id=db_product.supplier_id,
                    imei=imei_val.strip(),
                    vendido=False,
                    received_at=datetime.now(UTC),
                    acquisition_type='initial_stock',
                    received_notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                    received_by=current_user.username,
                )
                db.add(db_imei)
                db.add(
                    IMEIHistory(
                        imei=imei_val.strip(),
                        product_id=db_product.id,
                        location_id=loc_id,
                        supplier_id=db_product.supplier_id,
                        event_type='purchase',
                        reference_id=db_product.id,
                        reference_type='product_creation',
                        notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                        created_by=current_user.username,
                    )
                )
        
        # LEGACY: Si hay IMEIs sin ubicación (para compatibilidad V1)
        elif imeis and len(imeis) > 0:
            if product.is_serialized and cantidad_inicial > 0 and len(imeis) != cantidad_inicial:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"La cantidad de IMEIs ({len(imeis)}) debe coincidir con el stock inicial ({cantidad_inicial})"
                )

            # ProductIMEI ya está importado globalmente
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
                        supplier_id=db_product.supplier_id,
                        imei=imei_value.strip(),
                        vendido=False,
                        received_at=datetime.now(UTC),
                        acquisition_type='initial_stock',
                        received_notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                        received_by=current_user.username,
                    )
                    db.add(db_imei)
                    db.add(
                        IMEIHistory(
                            imei=imei_value.strip(),
                            product_id=db_product.id,
                            location_id=initial_location_id if initial_location_id else None,
                            supplier_id=db_product.supplier_id,
                            event_type='purchase',
                            reference_id=db_product.id,
                            reference_type='product_creation',
                            notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                            created_by=current_user.username,
                        )
                    )
        
        db.commit()
        db.refresh(db_product)
        
        return _serialize_product(db_product)
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        error_detail = str(getattr(e, "orig", e))
        if "product_imeis" in error_detail or "ix_product_imeis_imei" in error_detail:
            raise HTTPException(status_code=400, detail="El IMEI ya está registrado en el sistema")
        if "products" in error_detail and "sku" in error_detail.lower():
            raise HTTPException(status_code=400, detail=f"Ya existe un producto con el SKU '{product.sku}'")
        raise HTTPException(status_code=400, detail="No se pudo crear el producto porque ya existe un valor único registrado")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear producto: {str(e)}")

@router.get("/{product_id}", response_model=ProductResponse, dependencies=[Depends(check_permission("inventory:view"))])
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
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

    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        has_visible_stock = any(stock.location_id in accessible_location_ids for stock in product.stock_items)
        if not has_visible_stock:
            raise HTTPException(status_code=404, detail=f"El producto con ID {product_id} no fue encontrado")
    
    return _serialize_product(product, accessible_location_ids)


@router.put("/{product_id}", response_model=ProductResponse, dependencies=[Depends(check_permission("inventory:edit"))])
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
    if updates.costo is not None:
        nuevo_costo = Decimal(updates.costo)
        if nuevo_costo < 0:
            raise HTTPException(
                status_code=400,
                detail="El costo no puede ser negativo"
            )
        product.costo = nuevo_costo
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

    if updates.is_serialized is not None:
        product.is_serialized = updates.is_serialized

    if updates.activo is not None:
        product.activo = updates.activo

    try:
        db.commit()
        db.refresh(product)
        return _serialize_product(product)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar producto: {str(e)}")


@router.put("/{product_id}/stock", dependencies=[Depends(check_permission("inventory:edit"))])
def update_product_stock(
    product_id: int, 
    update: StockUpdate, 
    location_id: int = Query(..., description="ID de la ubicación donde actualizar el stock"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:edit"))
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
    require_location_access(db, current_user, location_id, "can_edit")

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
    
    # V2.0: Validar que no sea menor a lo reservado
    if update.cantidad_disponible < stock.cantidad_reservada:
        raise HTTPException(
            status_code=400,
            detail=f"El stock no puede ser menor a la cantidad reservada ({stock.cantidad_reservada}). Libere las reservas o cancele transferencias pendientes primero."
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
        usuario=current_user.username
    )
    db.add(history)
    log_audit_event(
        db,
        action="stock.manual_adjust",
        entity_type="stock",
        entity_id=stock.id,
        location_id=location_id,
        user=current_user,
        before_data={"cantidad_disponible": stock_anterior},
        after_data={"cantidad_disponible": update.cantidad_disponible},
    )

    try:
        db.commit()
        return {"message": "Stock actualizado", "stock_anterior": float(stock_anterior), "stock_nuevo": update.cantidad_disponible}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar stock: {str(e)}")


@router.post("/{product_id}/restock", response_model=ProductResponse, dependencies=[Depends(check_permission("inventory:edit"))])
def restock_product(
    product_id: int,
    payload: ProductRestockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reabastece inventario de un producto existente con trazabilidad de IMEIs."""
    require_location_access(db, current_user, payload.location_id, "can_receive_purchase")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"El producto con ID {product_id} no fue encontrado")

    location = db.query(Location).filter(Location.id == payload.location_id).first()
    if not location or not location.activo:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada o inactiva")

    supplier_name: Optional[str] = None
    if payload.supplier_id is not None:
        supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail=f"Proveedor con ID {payload.supplier_id} no encontrado")
        supplier_name = supplier.nombre

    imeis_limpios: List[str] = []
    if payload.imeis:
        imeis_limpios = [imei.strip() for imei in payload.imeis if imei and imei.strip()]

    if product.is_serialized:
        if len(imeis_limpios) == 0:
            raise HTTPException(
                status_code=400,
                detail="Este producto es serializado. Debe ingresar IMEIs para el reabastecimiento.",
            )
        if len(imeis_limpios) != payload.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"La cantidad de IMEIs ({len(imeis_limpios)}) debe coincidir con la cantidad a agregar ({payload.cantidad})",
            )
    elif len(imeis_limpios) > 0:
        raise HTTPException(
            status_code=400,
            detail="Este producto no es serializado. No debe enviar IMEIs.",
        )

    if len(set(imeis_limpios)) != len(imeis_limpios):
        raise HTTPException(status_code=400, detail="La lista de IMEIs contiene valores duplicados")

    if imeis_limpios:
        existentes = db.query(ProductIMEI).filter(ProductIMEI.imei.in_(imeis_limpios)).all()
        if existentes:
            raise HTTPException(
                status_code=400,
                detail=f"El IMEI '{existentes[0].imei}' ya está registrado en el sistema",
            )

    stock = db.query(Stock).filter(
        Stock.product_id == product_id,
        Stock.location_id == payload.location_id,
    ).first()

    stock_total_anterior = sum(
        int(stock_item.cantidad_disponible or 0)
        for stock_item in db.query(Stock).filter(Stock.product_id == product_id).all()
    )
    costo_anterior = Decimal(product.costo or 0)
    costo_compra = Decimal(payload.costo_unitario)
    stock_total_nuevo = stock_total_anterior + payload.cantidad
    if stock_total_anterior > 0 and costo_anterior > 0:
        costo_promedio_nuevo = (
            (costo_anterior * Decimal(stock_total_anterior)) + (costo_compra * Decimal(payload.cantidad))
        ) / Decimal(stock_total_nuevo)
    else:
        costo_promedio_nuevo = costo_compra
    costo_promedio_nuevo = costo_promedio_nuevo.quantize(Decimal("0.01"))

    if not stock:
        stock = Stock(
            product_id=product_id,
            location_id=payload.location_id,
            cantidad_disponible=0,
            cantidad_reservada=0,
        )
        db.add(stock)
        db.flush()

    stock_anterior = stock.cantidad_disponible
    stock.cantidad_disponible = stock_anterior + payload.cantidad
    product.costo = costo_promedio_nuevo

    notas_restock = f"Reabastecimiento manual de '{product.nombre}'"
    if supplier_name:
        notas_restock += f" | Proveedor: {supplier_name}"
    notas_restock += (
        f" | Costo compra: {costo_compra:.2f} {product.moneda}"
        f" | Costo promedio: {costo_promedio_nuevo:.2f} {product.moneda}"
    )
    if payload.notas:
        notas_restock += f" | Nota: {payload.notas.strip()}"

    db.add(
        StockHistory(
            product_id=product_id,
            location_id=payload.location_id,
            tipo_cambio='compra',
            cantidad=payload.cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=stock.cantidad_disponible,
            referencia_id=product_id,
            referencia_tipo='manual_adjustment',
            notas=notas_restock,
            usuario=current_user.username,
        )
    )

    for imei in imeis_limpios:
        db.add(
            ProductIMEI(
                product_id=product_id,
                location_id=payload.location_id,
                supplier_id=payload.supplier_id,
                imei=imei,
                vendido=False,
                received_at=datetime.now(UTC),
                acquisition_type='restock',
                received_notes=notas_restock,
                received_by=current_user.username,
            )
        )
        db.add(
            IMEIHistory(
                imei=imei,
                product_id=product_id,
                location_id=payload.location_id,
                supplier_id=payload.supplier_id,
                event_type='purchase',
                reference_id=product_id,
                reference_type='restock',
                notes=notas_restock,
                created_by=current_user.username,
            )
        )

    log_audit_event(
        db,
        action="stock.restock",
        entity_type="product",
        entity_id=product.id,
        location_id=payload.location_id,
        user=current_user,
        before_data={"costo": str(costo_anterior), "stock_total": stock_total_anterior},
        after_data={
            **payload.model_dump(),
            "costo_promedio_nuevo": str(costo_promedio_nuevo),
            "stock_total_nuevo": stock_total_nuevo,
        },
    )

    try:
        db.commit()
        product_refreshed = (
            db.query(Product)
            .options(
                joinedload(Product.stock_items).joinedload(Stock.location),
                joinedload(Product.imeis),
            )
            .filter(Product.id == product_id)
            .first()
        )
        if not product_refreshed:
            raise HTTPException(status_code=404, detail="Producto no encontrado después de reabastecer")
        return _serialize_product(product_refreshed)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al reabastecer producto: {str(e)}")


@router.post("/bulk", response_model=List[ProductResponse], status_code=201, dependencies=[Depends(check_permission("inventory:create"))])
def bulk_create_products(
    payload: dict, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:create"))
):
    """
    Crea múltiples productos en una sola operación.
    
    V2.0: Los productos son globales y el stock debe asignarse por ubicación.
    Si no se envía initial_location_id, se usará la primera tienda activa.
    """
    products_data = payload.get("products", [])
    if not isinstance(products_data, list) or len(products_data) == 0:
        raise HTTPException(status_code=400, detail="Se requiere una lista de productos")

    created_products = []
    seen_imeis: set[str] = set()

    try:
        # Ubicación por defecto si no se envía initial_location_id
        default_location = _get_default_editable_location(db, current_user)

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

            if product.categoria == CategoriaEnum.CELULAR and product.garantia_meses == 0:
                product.garantia_meses = 2
            if product.categoria == CategoriaEnum.CELULAR and not product.is_serialized:
                product.is_serialized = True

            product_data = product.model_dump(by_alias=True)
            cantidad_inicial = product_data.pop("stock_inicial", product_data.pop("cantidad_inicial", 0))
            initial_location_id = product_data.pop("initial_location_id", None)
            imeis_con_ubicacion = product_data.pop("imeis_con_ubicacion", None)

            # Campos legacy (compatibilidad) que NO existen en el modelo Product
            single_imei = product_data.pop("imei", None)
            legacy_imeis = product_data.pop("imeis", None) or []
            if single_imei:
                legacy_imeis.append(single_imei)

            # Determinar ubicación destino
            location = None
            if initial_location_id:
                location = _require_active_location_for_stock(db, current_user, initial_location_id)
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

            if product.is_serialized and cantidad_inicial > 0:
                imei_count = len(imeis_con_ubicacion or []) + len(legacy_imeis)
                if imei_count != cantidad_inicial:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Para productos serializados, la cantidad de IMEIs ({imei_count}) "
                            f"debe coincidir con el stock inicial ({cantidad_inicial})"
                        ),
                    )

            db_stock = Stock(
                product_id=db_product.id,
                location_id=location.id,
                cantidad_disponible=cantidad_inicial
            )
            db.add(db_stock)

            for imei_data in imeis_con_ubicacion or []:
                imei_val, loc_id = _extract_imei_location(imei_data)
                if loc_id != location.id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El IMEI '{imei_val}' debe estar en la ubicación inicial {location.id}",
                    )
                _require_active_location_for_stock(db, current_user, loc_id)
                if imei_val in seen_imeis or db.query(ProductIMEI).filter(ProductIMEI.imei == imei_val).first():
                    raise HTTPException(status_code=400, detail=f"El IMEI '{imei_val}' ya está registrado")
                seen_imeis.add(imei_val)
                db.add(ProductIMEI(
                    product_id=db_product.id,
                    location_id=loc_id,
                    supplier_id=db_product.supplier_id,
                    imei=imei_val,
                    vendido=False,
                    received_at=datetime.now(UTC),
                    acquisition_type='initial_stock',
                    received_notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                    received_by=current_user.username,
                ))
                db.add(IMEIHistory(
                    imei=imei_val,
                    product_id=db_product.id,
                    location_id=loc_id,
                    supplier_id=db_product.supplier_id,
                    event_type='purchase',
                    reference_id=db_product.id,
                    reference_type='product_creation_bulk',
                    notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                    created_by=current_user.username,
                ))

            for imei_raw in legacy_imeis:
                imei_val = str(imei_raw).strip()
                if not imei_val:
                    continue
                if imei_val in seen_imeis or db.query(ProductIMEI).filter(ProductIMEI.imei == imei_val).first():
                    raise HTTPException(status_code=400, detail=f"El IMEI '{imei_val}' ya está registrado")
                seen_imeis.add(imei_val)
                db.add(ProductIMEI(
                    product_id=db_product.id,
                    location_id=location.id,
                    supplier_id=db_product.supplier_id,
                    imei=imei_val,
                    vendido=False,
                    received_at=datetime.now(UTC),
                    acquisition_type='initial_stock',
                    received_notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                    received_by=current_user.username,
                ))
                db.add(IMEIHistory(
                    imei=imei_val,
                    product_id=db_product.id,
                    location_id=location.id,
                    supplier_id=db_product.supplier_id,
                    event_type='purchase',
                    reference_id=db_product.id,
                    reference_type='product_creation_bulk',
                    notes=f"Stock inicial del producto '{product.nombre}' (SKU: {product.sku})",
                    created_by=current_user.username,
                ))

            created_products.append((db_product, db_stock))

        db.commit()

        return [_serialize_product(product) for product, _ in created_products]
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear productos: {str(e)}")


@router.delete("/{product_id}", status_code=204, dependencies=[Depends(check_permission("inventory:delete"))])
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
    
    # Verificar si está en órdenes históricas (completadas/validadas/canceladas)
    historical_order_items = db.query(OrderItem).join(Order).filter(
        OrderItem.product_id == product_id,
        Order.estado.in_(['completada', 'validada', 'cancelada'])
    ).count()
    
    if historical_order_items > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el producto porque está referenciado en {historical_order_items} órdenes históricas. Use 'activo=false' para desactivarlo sin perder trazabilidad."
        )

    imei_history_count = db.query(IMEIHistory).filter(
        IMEIHistory.product_id == product_id
    ).count()

    if imei_history_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el producto porque tiene {imei_history_count} registro(s) de historial IMEI. Use 'activo=false' para desactivarlo sin perder trazabilidad."
        )

    # Verificar stock reservado y transferencias pendientes
    from app.models import StockTransfer

    reserved_stock = db.query(Stock).filter(
        Stock.product_id == product_id,
        Stock.cantidad_reservada > 0
    ).first()

    if reserved_stock:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el producto porque tiene stock reservado en transferencias pendientes."
        )

    pending_transfer = db.query(StockTransfer).filter(
        StockTransfer.product_id == product_id,
        StockTransfer.estado == 'pendiente'
    ).first()

    if pending_transfer:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el producto porque tiene una transferencia pendiente (ID {pending_transfer.id})."
        )
    
    try:
        # V2.0: Eliminar IMEIs asociados primero
        # ProductIMEI ya está importado globalmente
        imeis = db.query(ProductIMEI).filter(ProductIMEI.product_id == product_id).all()
        for imei in imeis:
            db.delete(imei)
        
        # V2.0: Eliminar todos los stocks por ubicación
        if hasattr(product, 'stock_items') and product.stock_items:
            for stock_item in product.stock_items:
                db.delete(stock_item)
        
        # Luego eliminar el producto
        db.delete(product)
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el producto porque tiene historial o referencias asociadas. Use 'activo=false' para desactivarlo sin perder trazabilidad."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar producto: {str(e)}")


@router.post("/{product_id}/stock/location/{location_id}", dependencies=[Depends(check_permission("inventory:edit"))])
def set_product_stock_at_location(
    product_id: int,
    location_id: int,
    cantidad: int = Query(..., ge=0, description="Cantidad de stock en esta ubicación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Establecer o actualizar el stock de un producto en una ubicación específica.
    """
    # Verificar que el producto existe
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    location = _require_active_location_for_stock(db, current_user, location_id)
    
    # Buscar o crear el registro de stock
    stock = db.query(Stock).filter(
        Stock.product_id == product_id,
        Stock.location_id == location_id
    ).first()
    
    stock_anterior = stock.cantidad_disponible if stock else 0
    reservado = stock.cantidad_reservada if stock else 0
    
    if reservado > cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede establecer stock menor al reservado. Reservado: {reservado}, Nuevo stock: {cantidad}"
        )
    
    if stock:
        stock.cantidad_disponible = cantidad
    else:
        stock = Stock(
            product_id=product_id,
            location_id=location_id,
            cantidad_disponible=cantidad,
            cantidad_reservada=0
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
        usuario=current_user.username
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


@router.get("/{product_id}/stock/total", dependencies=[Depends(check_permission("inventory:view"))])
def get_product_total_stock(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Obtener el stock total de un producto sumando todas las ubicaciones.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    total_query = db.query(func.sum(Stock.cantidad_disponible - func.coalesce(Stock.cantidad_reservada, 0))).filter(
        Stock.product_id == product_id
    )
    if accessible_location_ids is not None:
        total_query = total_query.filter(Stock.location_id.in_(accessible_location_ids))
    total = max(int(total_query.scalar() or 0), 0)
    
    return {
        "product_id": product_id,
        "product_name": product.nombre,
        "sku": product.sku,
        "total_stock": total
    }


@router.get("/{product_id}/stock/by-location", response_model=List[StockByLocationResponse], dependencies=[Depends(check_permission("inventory:view"))])
def get_product_stock_by_location(
    product_id: int,
    include_inactive_locations: bool = Query(False, description="Incluir ubicaciones inactivas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Devuelve el stock del producto desglosado por ubicación (V2.0).

    Esta ruta es usada por el frontend para mostrar stock por tienda/bodega.
    Alinea el contrato con `apiClient.getStockByLocation` que esperaba este endpoint.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    query = db.query(Stock).join(Location).filter(Stock.product_id == product_id)
    accessible_location_ids = get_accessible_location_ids(db, current_user, "can_view")
    if accessible_location_ids is not None:
        query = query.filter(Stock.location_id.in_(accessible_location_ids))
    if not include_inactive_locations:
        query = query.filter(Location.activo == True)

    stock_items = query.all()

    result: List[StockByLocationResponse] = []
    for stock in stock_items:
        # Calcular stock libre para evitar mostrar unidades reservadas como disponibles
        stock_libre = stock.cantidad_disponible - stock.cantidad_reservada
        if stock_libre < 0:
            stock_libre = 0

        en_transito_salida = db.query(func.coalesce(func.sum(StockTransfer.cantidad), 0)).filter(
            StockTransfer.product_id == product_id,
            StockTransfer.from_location_id == stock.location_id,
            StockTransfer.estado == "pendiente",
        ).scalar() or 0
        en_transito_entrada = db.query(func.coalesce(func.sum(StockTransfer.cantidad), 0)).filter(
            StockTransfer.product_id == product_id,
            StockTransfer.to_location_id == stock.location_id,
            StockTransfer.estado == "pendiente",
        ).scalar() or 0

        location = stock.location
        result.append(StockByLocationResponse(
            id=stock.id,
            product_id=stock.product_id,
            location_id=stock.location_id,
            cantidad_disponible=stock.cantidad_disponible,
            cantidad_reservada=stock.cantidad_reservada,
            cantidad_defectuosa=stock.cantidad_defectuosa or 0,
            stock_libre=stock_libre,
            en_transito_salida=int(en_transito_salida),
            en_transito_entrada=int(en_transito_entrada),
            location=LocationResponse(
                id=location.id,
                nombre=location.nombre,
                tipo=location.tipo,
                direccion=location.direccion,
                activo=location.activo,
                created_at=location.created_at,
                updated_at=location.updated_at
            ) if location else None
        ))

    return result
