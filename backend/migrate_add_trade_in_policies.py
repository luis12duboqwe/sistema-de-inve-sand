from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from app.database import Base

# Definir el modelo aquí temporalmente para el script de migración
class TradeInPolicy(Base):
    __tablename__ = "trade_in_policies"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String, default="model_rejection") # model_rejection, brand_rejection
    pattern = Column(String, nullable=False) # e.g., "iPhone XR", "Xiaomi"
    action = Column(String, default="reject") # reject, warning
    reason = Column(String, nullable=True) # "No tiene mercado", "Muy viejo"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def migrate():
    engine = create_engine(settings.database_url)
    print("Creando tabla trade_in_policies...")
    TradeInPolicy.__table__.create(bind=engine, checkfirst=True)
    print("Tabla creada exitosamente.")

if __name__ == "__main__":
    migrate()
