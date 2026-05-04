#!/usr/bin/env python3
"""
Migración: Agregar tabla ProcessedMessage para deduplicación persistente.

Crea la tabla processed_messages para almacenar un registro de mensajes
ya procesados, permitiendo deduplicación persistente entre reinicios.
"""

from app.database import engine, SessionLocal
from app.models.ai import ProcessedMessage
from app.database import Base


def migrate():
    """Crea la tabla de mensajes procesados."""
    print("Creando tabla processed_messages...")
    
    try:
        # Crear solo la tabla ProcessedMessage
        ProcessedMessage.__table__.create(bind=engine, checkfirst=True)
        print("✓ Tabla processed_messages creada exitosamente")
    except Exception as e:
        print(f"⚠ Table ya existe o error: {e}")


if __name__ == "__main__":
    migrate()
