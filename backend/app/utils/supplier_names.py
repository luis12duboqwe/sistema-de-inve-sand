"""Supplier-name identity shared by ORM writes, API guards and migrations."""

import hashlib


def normalize_supplier_name(name: str) -> str:
    """Return the display name using the supplier contract's existing trim rule."""
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("El nombre del proveedor no puede estar vacío")
    return normalized


def supplier_name_key(name: str) -> str:
    """Return the existing case-insensitive logical identity for a supplier."""
    return normalize_supplier_name(name).lower()


def supplier_name_hash(name: str) -> str:
    """Return a fixed-width database key for the full logical supplier identity."""
    try:
        payload = supplier_name_key(name).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("El nombre del proveedor contiene Unicode inválido") from exc
    return hashlib.sha256(payload).hexdigest()


__all__ = ["normalize_supplier_name", "supplier_name_hash", "supplier_name_key"]
