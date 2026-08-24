from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship, validates

from app.database import Base
from app.utils.bank_names import bank_name_key, normalize_bank_name


class Bank(Base):
    """Bancos que ofrecen financiamiento."""

    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    name_normalized = Column(String(255), nullable=False, unique=True, index=True)
    active = Column(Boolean, default=True, nullable=False)
    normal_card_rate = Column(Numeric(5, 4), default=0.0, nullable=False)

    financing_options = relationship("FinancingOption", back_populates="bank", cascade="all, delete-orphan")

    @validates("name")
    def _canonicalize_name(self, _key: str, value: str) -> str:
        normalized = normalize_bank_name(value)
        self.name_normalized = bank_name_key(normalized)
        return normalized


class FinancingOption(Base):
    """Plazos y tasas por banco."""

    __tablename__ = "financing_options"

    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True)
    months = Column(Integer, nullable=False)
    rate = Column(Numeric(5, 4), nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    bank = relationship("Bank", back_populates="financing_options")


__all__ = ["Bank", "FinancingOption"]