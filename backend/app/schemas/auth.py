"""Esquemas relacionados con autenticación JWT."""

from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Respuesta estándar del endpoint de autenticación."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Datos embebidos dentro del token JWT."""

    username: Optional[str] = None
