"""Compatibility re-export for the stable supplier identity helpers."""

from app.supplier_identity import (
    normalize_supplier_name,
    supplier_name_hash,
    supplier_name_key,
)


__all__ = ["normalize_supplier_name", "supplier_name_hash", "supplier_name_key"]
