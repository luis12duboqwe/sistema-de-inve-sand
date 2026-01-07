import sys
import os
sys.path.append(os.path.abspath('.'))

from app.database import SessionLocal
from app.routers.forecasting import get_forecasts
from app.models import User

# Mock user
mock_user = User(id=1, username="admin", role_id=1)

db = SessionLocal()
try:
    print("Running forecast calculation...")
    forecasts = get_forecasts(db=db, current_user=mock_user)
    print(f"Generated {len(forecasts)} forecasts.")
    for f in forecasts[:5]:
        print(f"Product: {f.productName}, Stock: {f.currentStock}, Pred 30d: {f.predictedSalesNext30Days}, Trend: {f.trend}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
