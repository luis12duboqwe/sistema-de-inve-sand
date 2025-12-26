from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.database import get_db
from app.models import Order, OrderItem, Product, Stock, User
from app.auth import get_current_active_user, check_permission
from pydantic import BaseModel

router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])

class SalesForecast(BaseModel):
    productId: int
    productName: str
    currentStock: int
    averageDailySales: float
    predictedSalesNext7Days: int
    predictedSalesNext30Days: int
    daysUntilStockout: int
    restockRecommendation: int
    confidence: float
    trend: str

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
    
    forecasts = []

    for product in products:
        # Calcular stock total
        total_stock = 0
        if product.stock_items:
            total_stock = sum(
                max((s.cantidad_disponible or 0) - (s.cantidad_reservada or 0), 0) 
                for s in product.stock_items
            )

        # Ventas recientes (30 días)
        recent_sales = db.query(func.sum(OrderItem.cantidad)).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.created_at >= thirty_days_ago,
            Order.estado != 'cancelada'
        ).scalar() or 0

        # Ventas anteriores (30-60 días)
        older_sales = db.query(func.sum(OrderItem.cantidad)).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.created_at >= sixty_days_ago,
            Order.created_at < thirty_days_ago,
            Order.estado != 'cancelada'
        ).scalar() or 0

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
            productId=product.id,
            productName=f"{product.marca} {product.modelo}",
            currentStock=total_stock,
            averageDailySales=round(recent_daily_sales, 2),
            predictedSalesNext7Days=predicted_7,
            predictedSalesNext30Days=predicted_30,
            daysUntilStockout=days_until_stockout,
            restockRecommendation=restock_recommendation,
            confidence=round(confidence, 2),
            trend=trend
        ))
    
    # Ordenar por urgencia (días hasta agotarse)
    forecasts.sort(key=lambda x: x.daysUntilStockout)
    
    return forecasts
