"""Modelo de configuración del sistema."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class SystemConfig(Base):
    """Configuraciones globales del sistema almacenadas en BD."""

    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    updated_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<SystemConfig key={self.key!r}>"


__all__ = ["SystemConfig"]
