from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.auth import check_permission
from app.database import get_db
from app.models import User
from app.schemas import SalesForecast
from app.services.forecasting_service import generate_sales_forecasts

router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])

@router.get("/predict", response_model=List[SalesForecast])
def get_forecasts(
    days_history: int = Query(60, ge=30, le=365),
    location_id: Optional[int] = None,
    product_ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("reports:view"))
):
    """Genera predicciones de ventas y recomendaciones de reabastecimiento."""
    ids_filter = product_ids or None
    return generate_sales_forecasts(
        db,
        days_history=days_history,
        product_ids=ids_filter,
        location_id=location_id,
    )
