"""Canonical bank-name normalization shared by writes and schema migrations."""

import unicodedata


def normalize_bank_name(name: str) -> str:
    """Return the display name stored by canonical financing write paths."""
    normalized = name.strip()
    if len(normalized) < 2:
        raise ValueError("El nombre del banco debe tener al menos 2 caracteres")
    return normalized


def bank_name_key(name: str) -> str:
    """Return a Unicode-normalized, case-insensitive uniqueness key."""
    display_name = normalize_bank_name(name)
    # NFKC makes canonically/compatibly equivalent spellings share identity
    # (e.g. composed/decomposed accents), while the display name stays intact.
    return unicodedata.normalize("NFKC", display_name.casefold())


__all__ = ["bank_name_key", "normalize_bank_name"]
