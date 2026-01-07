from app.database import SessionLocal
from app.models import Product, Order, Location, SalesProfile

db = SessionLocal()
print(f"Products: {db.query(Product).count()}")
print(f"Orders: {db.query(Order).count()}")
print(f"Locations: {db.query(Location).count()}")
print(f"SalesProfiles: {db.query(SalesProfile).count()}")
