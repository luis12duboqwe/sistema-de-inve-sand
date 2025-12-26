from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.models import IMEIHistory, Product, Location, ProductIMEI, Order, User
from app.schemas import IMEIHistoryResponse
from app.auth import get_current_active_user, check_permission

router = APIRouter(prefix="/api/imeis", tags=["imeis"])

@router.get("/{imei}/warranty-status")
def check_warranty_status(
    imei: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view"))
):
    """
    Verifica el estado de garantía de un IMEI.
    Busca la fecha de venta y calcula si aún está vigente según los meses de garantía del producto.
    """
    # 1. Buscar el IMEI en ProductIMEI para obtener el producto y la orden de venta
    product_imei = db.query(ProductIMEI).filter(ProductIMEI.imei == imei).first()
    
    if not product_imei:
        raise HTTPException(status_code=404, detail="IMEI no encontrado en el sistema")
        
    if not product_imei.vendido or not product_imei.order_id:
        return {
            "imei": imei,
            "status": "en_stock",
            "detail": "El producto aún no ha sido vendido, garantía no activa."
        }
        
    # 2. Obtener la orden para saber la fecha de venta
    order = db.query(Order).filter(Order.id == product_imei.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden de venta no encontrada")
        
    # 3. Obtener el producto para saber los meses de garantía
    product = product_imei.product
    if not product:
        raise HTTPException(status_code=404, detail="Producto asociado no encontrado")
        
    sale_date = order.created_at
    warranty_months = product.garantia_meses
    
    if warranty_months == 0:
        return {
            "imei": imei,
            "product": product.nombre,
            "status": "sin_garantia",
            "sale_date": sale_date,
            "detail": "Este producto no tiene garantía."
        }
        
    # Calcular expiración
    # Aproximación: 1 mes = 30 días
    expiration_date = sale_date + timedelta(days=warranty_months * 30)
    
    # Manejar timezone awareness
    now = datetime.now(sale_date.tzinfo) if sale_date.tzinfo else datetime.now()
    remaining_days = (expiration_date - now).days
    
    is_active = remaining_days > 0
    
    return {
        "imei": imei,
        "product": product.nombre,
        "status": "activa" if is_active else "expirada",
        "sale_date": sale_date,
        "warranty_months": warranty_months,
        "expiration_date": expiration_date,
        "remaining_days": max(0, remaining_days),
        "customer": order.customer_name
    }

@router.get("/history/{imei}", response_model=List[IMEIHistoryResponse])
def get_imei_history(
    imei: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view"))
):
    history = db.query(IMEIHistory).filter(IMEIHistory.imei == imei).order_by(IMEIHistory.created_at.desc()).all()
    
    # Enrich with names
    result = []
    for h in history:
        resp = IMEIHistoryResponse.model_validate(h)
        if h.product:
            resp.product_name = h.product.nombre
        if h.location:
            resp.location_name = h.location.nombre
        result.append(resp)
        
    return result
