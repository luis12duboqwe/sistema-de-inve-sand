from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.database import get_db
from app.models import Order, OrderItem, Product, Stock, User
from app.auth import get_current_active_user, check_permission
from app.schemas import SalesForecast

router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])

@router.get("/predict", response_model=List[SalesForecast])
def get_forecasts(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """
    Genera predicciones de ventas y recomendaciones de reabastecimiento.
    Calculado en el servidor para mejor escalabilidad.
    """
    # 1. Fechas
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    # 2. Obtener productos activos
    products = db.query(Product).filter(Product.activo == True).all()
    
    # 3. Pre-fetch stock para evitar N+1
    # Sumar stock de todas las ubicaciones por producto
    stock_data = db.query(
        Stock.product_id,
        func.sum(Stock.cantidad).label("total_stock"),
        func.sum(Stock.cantidad_reservada).label("total_reserved")
    ).group_by(Stock.product_id).all()
    
    stock_map = {}
    for pid, total, reserved in stock_data:
        # Stock disponible real = total - reservado
        available = max((total or 0) - (reserved or 0), 0)
        stock_map[pid] = available

    # 4. Pre-fetch ventas para evitar N+1
    # Ventas recientes (últimos 30 días)
    recent_sales_data = db.query(
        OrderItem.product_id,
        func.sum(OrderItem.cantidad)
    ).join(Order).filter(
        Order.created_at >= thirty_days_ago,
        Order.estado != 'cancelada'
    ).group_by(OrderItem.product_id).all()
    
    recent_sales_map = {pid: qty for pid, qty in recent_sales_data}

    # Ventas anteriores (30-60 días)
    older_sales_data = db.query(
        OrderItem.product_id,
        func.sum(OrderItem.cantidad)
    ).join(Order).filter(
        Order.created_at >= sixty_days_ago,
        Order.created_at < thirty_days_ago,
        Order.estado != 'cancelada'
    ).group_by(OrderItem.product_id).all()
    
    older_sales_map = {pid: qty for pid, qty in older_sales_data}

    forecasts = []

    for product in products:
        total_stock = stock_map.get(product.id, 0)
        recent_sales = recent_sales_map.get(product.id, 0)
        older_sales = older_sales_map.get(product.id, 0)

        recent_daily_sales = float(recent_sales) / 30
        older_daily_sales = float(older_sales) / 30

        # Tendencia
        trend = "stable"
        if recent_daily_sales > older_daily_sales * 1.1:
            trend = "increasing"
        elif recent_daily_sales < older_daily_sales * 0.9:
            trend = "decreasing"

        # Factor de crecimiento (simple)
        growth_factor = 1.0
        if older_daily_sales > 0:
            growth_factor = recent_daily_sales / older_daily_sales
            # Limitar crecimiento explosivo para predicciones conservadoras
            growth_factor = min(max(growth_factor, 0.5), 2.0) 
        
        predicted_daily_sales = recent_daily_sales * growth_factor
        
        predicted_7 = int(predicted_daily_sales * 7)
        predicted_30 = int(predicted_daily_sales * 30)
        
        days_until_stockout = 999
        if predicted_daily_sales > 0:
            days_until_stockout = int(total_stock / predicted_daily_sales)
        
        restock_recommendation = max(0, predicted_30 - total_stock)
        
        # Confianza simple basada en volumen de datos
        confidence = 0.5
        if recent_sales > 10: confidence += 0.2
        if older_sales > 10: confidence += 0.2
        if trend == "stable": confidence += 0.1
        confidence = min(confidence, 1.0)

        forecasts.append(SalesForecast(
            product_id=product.id,
            product_name=f"{product.marca} {product.modelo}",
            current_stock=total_stock,
            average_daily_sales=round(recent_daily_sales, 2),
            predicted_sales_next_7_days=predicted_7,
            predicted_sales_next_30_days=predicted_30,
            days_until_stockout=days_until_stockout,
            restock_recommendation=restock_recommendation,
            confidence=round(confidence, 2),
            trend=trend
        ))
    
    # Ordenar por urgencia (días hasta agotarse)
    forecasts.sort(key=lambda x: x.days_until_stockout)
    
    return forecasts
