from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.auth import check_permission
from app.database import get_db
from app.models import User
from app.schemas import SalesForecast
from app.services.forecasting_service import generate_sales_forecasts
from app.utils.location_access import get_accessible_location_ids, require_location_access

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
    scoped_locations = get_accessible_location_ids(db, current_user, "can_view")
    if location_id is not None:
        require_location_access(db, current_user, location_id, "can_view")
        scoped_locations = [location_id]
    if scoped_locations is not None and not scoped_locations:
        return []
    return generate_sales_forecasts(
        db,
        days_history=days_history,
        product_ids=ids_filter,
        location_ids=scoped_locations,
    )
