"""Stable location-name identity shared by model writes and migrations."""

import hashlib
import unicodedata


def normalize_location_name(name: str) -> str:
    """Return the trimmed display name accepted by location write paths."""
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("El nombre de la ubicación no puede estar vacío")
    return normalized


def location_name_key(name: str) -> str:
    """Return a deterministic Unicode-aware logical location identity."""
    display_name = normalize_location_name(name)
    compatibility_normalized = unicodedata.normalize("NFKC", display_name).strip()
    folded = compatibility_normalized.casefold()
    return unicodedata.normalize("NFKC", folded).strip()


def location_name_hash(name: str) -> str:
    """Return an index-safe digest of the complete canonical location identity."""
    return hashlib.sha256(location_name_key(name).encode("utf-8")).hexdigest()


__all__ = ["normalize_location_name", "location_name_hash", "location_name_key"]
