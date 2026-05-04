import math
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_active_user, check_permission
from app.database import get_db
from app.models import IMEIHistory, Location, Order, Product, ProductIMEI, User
from app.schemas import IMEIDetailResponse, IMEIHistoryResponse, PaginatedResponse, ProductIMEIResponse

router = APIRouter(prefix="/api/imeis", tags=["imeis"])


def _serialize_product_imei(record: ProductIMEI) -> ProductIMEIResponse:
    return ProductIMEIResponse(
        id=record.id,
        product_id=record.product_id,
        location_id=record.location_id,
        supplier_id=record.supplier_id,
        imei=record.imei,
        vendido=record.vendido,
        order_id=record.order_id,
        transfer_id=record.transfer_id,
        received_at=record.received_at,
        sold_at=record.sold_at,
        acquisition_type=record.acquisition_type,
        received_notes=record.received_notes,
        received_by=record.received_by,
        created_at=record.created_at,
        product_name=record.product.nombre if record.product else None,
        location_name=record.location.nombre if record.location else None,
        supplier_name=record.supplier.nombre if record.supplier else None,
    )


def _build_imei_status(record: ProductIMEI) -> str:
    if record.transfer_id:
        return "en_transito"
    if record.vendido:
        return "vendido"
    return "en_stock"


def _build_warranty_expiration(record: ProductIMEI) -> Optional[datetime]:
    if not record.sold_at or not record.product or not record.product.garantia_meses:
        return None
    return record.sold_at + timedelta(days=record.product.garantia_meses * 30)


@router.get("", response_model=PaginatedResponse[ProductIMEIResponse])
def list_product_imeis(
    vendido: Optional[bool] = Query(None, description="Filtrar por IMEIs vendidos"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    search: Optional[str] = Query(None, description="Buscar por IMEI"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(100, ge=10, le=500, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    """Lista global de IMEIs con paginación para sincronización offline."""

    query = db.query(ProductIMEI).options(
        joinedload(ProductIMEI.product),
        joinedload(ProductIMEI.location),
        joinedload(ProductIMEI.supplier),
        joinedload(ProductIMEI.order),
    )

    if vendido is not None:
        query = query.filter(ProductIMEI.vendido == vendido)
    if location_id is not None:
        query = query.filter(ProductIMEI.location_id == location_id)
    if product_id is not None:
        query = query.filter(ProductIMEI.product_id == product_id)
    if search:
        like_term = f"%{search}%"
        query = query.filter(ProductIMEI.imei.ilike(like_term))

    total = query.count()
    offset = (page - 1) * per_page
    imeis = (
        query.order_by(ProductIMEI.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    items = [_serialize_product_imei(record) for record in imeis]

    pages = math.ceil(total / per_page) if total else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/history", response_model=PaginatedResponse[IMEIHistoryResponse])
def list_imei_history(
    imei: Optional[str] = Query(None, description="Filtrar por IMEI"),
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    location_id: Optional[int] = Query(None, description="Filtrar por ubicación"),
    days: Optional[int] = Query(90, ge=1, le=365, description="Días a considerar"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(100, ge=10, le=500, description="Resultados por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view")),
):
    """Devuelve el historial global de IMEIs con paginación."""

    query = db.query(IMEIHistory).options(
        joinedload(IMEIHistory.product),
        joinedload(IMEIHistory.location),
        joinedload(IMEIHistory.supplier),
    )

    if imei:
        query = query.filter(IMEIHistory.imei == imei)
    if product_id is not None:
        query = query.filter(IMEIHistory.product_id == product_id)
    if location_id is not None:
        query = query.filter(IMEIHistory.location_id == location_id)
    if days is not None:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(IMEIHistory.created_at >= cutoff)

    total = query.count()
    offset = (page - 1) * per_page
    entries = (
        query.order_by(IMEIHistory.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    results: List[IMEIHistoryResponse] = []
    for entry in entries:
        payload = IMEIHistoryResponse.model_validate(entry)
        if entry.product:
            payload.product_name = entry.product.nombre
        if entry.location:
            payload.location_name = entry.location.nombre
        if entry.supplier:
            payload.supplier_name = entry.supplier.nombre
        results.append(payload)

    pages = math.ceil(total / per_page) if total else 0
    return PaginatedResponse(
        items=results,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )

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


@router.get("/detail/{imei}", response_model=IMEIDetailResponse)
def get_imei_detail(
    imei: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("inventory:view"))
):
    record = (
        db.query(ProductIMEI)
        .options(
            joinedload(ProductIMEI.product),
            joinedload(ProductIMEI.location),
            joinedload(ProductIMEI.supplier),
            joinedload(ProductIMEI.order),
        )
        .filter(ProductIMEI.imei == imei)
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="IMEI no encontrado en el sistema")

    serialized = _serialize_product_imei(record)
    return IMEIDetailResponse(
        **serialized.model_dump(),
        product_sku=record.product.sku if record.product else None,
        customer_name=record.order.customer_name if record.order else None,
        customer_phone=record.order.customer_phone if record.order else None,
        status_label=_build_imei_status(record),
        warranty_months=record.product.garantia_meses if record.product else None,
        warranty_expires_at=_build_warranty_expiration(record),
    )

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
        if h.supplier:
            resp.supplier_name = h.supplier.nombre
        result.append(resp)
        
    return result
