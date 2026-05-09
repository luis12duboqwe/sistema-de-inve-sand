"""Helpers compartidos para el código de validación de cierre diario."""

import hashlib
import logging

from passlib.exc import UnknownHashError
from sqlalchemy.orm import Session

from app.auth import get_password_hash, verify_password
from app.models import SystemConfig

logger = logging.getLogger(__name__)

DAILY_CLOSE_CODE_KEY = "daily_close_validation_code"


def hash_daily_close_code(code: str) -> str:
    return get_password_hash(code.strip())


def legacy_hash_daily_close_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode()).hexdigest()


def get_daily_close_code_hash(db: Session) -> str | None:
    stored = db.query(SystemConfig).filter(SystemConfig.key == DAILY_CLOSE_CODE_KEY).first()
    return str(stored.value) if stored and stored.value else None


def verify_daily_close_code(stored_hash: str, code: str) -> bool:
    if not stored_hash:
        return False

    try:
        return verify_password(code.strip(), stored_hash)
    except (ValueError, UnknownHashError):
        logger.debug("Código de cierre diario usa hash legado; verificando SHA-256")
        return stored_hash == legacy_hash_daily_close_code(code)