from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from app.database import get_db
from app.models import Order, OrderItem, Product, Profile, Stock
from app.schemas import OrderCreate, OrderResponse, OrderListResponse, ProductResponse

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.get("", response_model=List[OrderListResponse])
def list_orders(
    profile_slug: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    
    if profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Perfil no encontrado")
        query = query.filter(Order.profile_id == profile.id)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return orders

@router.post("", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.slug == order.profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil '{order.profile_slug}' no encontrado")
    
    if not order.items:
        raise HTTPException(status_code=400, detail="La orden debe contener al menos un producto")
    
    total = Decimal("0.00")
    order_items_data = []
    
    for item in order.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.activo == True
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=404, 
                detail=f"Producto con ID {item.product_id} no encontrado o inactivo"
            )
        
        stock = db.query(Stock).filter(Stock.product_id == item.product_id).first()
        if not stock:
            raise HTTPException(
                status_code=400,
                detail=f"El producto '{product.nombre}' no tiene stock registrado"
            )
        
        if stock.cantidad_disponible < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{product.nombre}'. Disponible: {stock.cantidad_disponible}, Solicitado: {item.cantidad}"
            )
        
        precio_unitario = Decimal(str(product.precio))
        subtotal = precio_unitario * item.cantidad
        
        if not item.es_regalo_promocion:
            total += subtotal
        
        order_items_data.append({
            "product": product,
            "stock": stock,
            "cantidad": item.cantidad,
            "precio_unitario": precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion
        })
    
    db_order = Order(
        profile_id=profile.id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        canal=order.canal,
        metodo_pago=order.metodo_pago,
        total=total,
        estado="pendiente"
    )
    db.add(db_order)
    db.flush()
    
    db_order_items = []
    for item_data in order_items_data:
        db_order_item = OrderItem(
            order_id=db_order.id,
            product_id=item_data["product"].id,
            cantidad=item_data["cantidad"],
            precio_unitario=item_data["precio_unitario"],
            es_regalo_promocion=item_data["es_regalo_promocion"]
        )
        db.add(db_order_item)
        db_order_items.append(db_order_item)
        
        item_data["stock"].cantidad_disponible -= item_data["cantidad"]
    
    db.commit()
    db.refresh(db_order)
    
    for item in db_order_items:
        db.refresh(item)
    
    items_response = []
    for item in db_order.items:
        product = item.product
        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion,
            "product": ProductResponse(
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
        })
    
    return OrderResponse(
        id=db_order.id,
        profile_id=db_order.profile_id,
        customer_name=db_order.customer_name,
        customer_phone=db_order.customer_phone,
        canal=db_order.canal,
        metodo_pago=db_order.metodo_pago,
        total=db_order.total,
        estado=db_order.estado,
        created_at=db_order.created_at,
        items=items_response
    )

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    items_response = []
    for item in order.items:
        product = item.product
        items_response.append({
            "id": item.id,
            "product_id": item.product_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "es_regalo_promocion": item.es_regalo_promocion,
            "product": ProductResponse(
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
        })
    
    return OrderResponse(
        id=order.id,
        profile_id=order.profile_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        canal=order.canal,
        metodo_pago=order.metodo_pago,
        total=order.total,
        estado=order.estado,
        created_at=order.created_at,
        items=items_response
    )
