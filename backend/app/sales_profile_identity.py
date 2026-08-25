"""Stable sales-profile slug identity shared by model writes and migrations."""

import hashlib
import unicodedata


def normalize_sales_profile_slug(slug: str) -> str:
    """Return the trimmed display slug accepted by sales-profile write paths."""
    normalized = (slug or "").strip()
    if not normalized:
        raise ValueError("El slug del perfil de venta no puede estar vacío")
    return normalized


def sales_profile_slug_key(slug: str) -> str:
    """Return a deterministic Unicode-aware logical slug identity."""
    display_slug = normalize_sales_profile_slug(slug)
    compatibility_normalized = unicodedata.normalize("NFKC", display_slug).strip()
    folded = compatibility_normalized.casefold()
    return unicodedata.normalize("NFKC", folded).strip()


def sales_profile_slug_hash(slug: str) -> str:
    """Return an index-safe digest of the complete canonical slug identity."""
    return hashlib.sha256(sales_profile_slug_key(slug).encode("utf-8")).hexdigest()


__all__ = [
    "normalize_sales_profile_slug",
    "sales_profile_slug_hash",
    "sales_profile_slug_key",
]
