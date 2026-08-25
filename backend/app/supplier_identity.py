"""Stable supplier-name identity shared by model writes and migrations."""

import hashlib
import unicodedata


def normalize_supplier_name(name: str) -> str:
    """Return the trimmed display name accepted by supplier write paths."""
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("El nombre del proveedor no puede estar vacío")
    return normalized


def supplier_name_key(name: str) -> str:
    """Return a deterministic Unicode-aware logical supplier identity."""
    display_name = normalize_supplier_name(name)
    compatibility_normalized = unicodedata.normalize("NFKC", display_name).strip()
    folded = compatibility_normalized.casefold()
    return unicodedata.normalize("NFKC", folded).strip()


def supplier_name_hash(name: str) -> str:
    """Return an index-safe digest of the complete canonical supplier identity."""
    return hashlib.sha256(supplier_name_key(name).encode("utf-8")).hexdigest()


__all__ = ["normalize_supplier_name", "supplier_name_hash", "supplier_name_key"]
