"""Canonical bank-name normalization shared by writes and schema migrations."""

import hashlib
import unicodedata


_UNSAFE_UNICODE_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})


def normalize_bank_name(name: str) -> str:
    """Return the display name stored by canonical financing write paths."""
    normalized = name.strip()
    if len(normalized) < 2:
        raise ValueError("El nombre del banco debe tener al menos 2 caracteres")
    if any(unicodedata.category(char) in _UNSAFE_UNICODE_CATEGORIES for char in normalized):
        raise ValueError("El nombre del banco contiene caracteres Unicode no permitidos")
    return normalized


def bank_name_key(name: str) -> str:
    """Return the stable Unicode-aware logical identity for a bank name."""
    display_name = normalize_bank_name(name)
    # Compatibility normalization can itself introduce edge whitespace. Strip
    # after each normalization pass so compatibility-equivalent spellings cannot
    # diverge merely because one form materializes that whitespace later.
    compatibility_normalized = unicodedata.normalize("NFKC", display_name).strip()
    folded = compatibility_normalized.casefold()
    return unicodedata.normalize("NFKC", folded).strip()


def bank_name_hash(name: str) -> str:
    """Return an index-safe digest of the full canonical bank identity."""
    return hashlib.sha256(bank_name_key(name).encode("utf-8")).hexdigest()


__all__ = ["bank_name_hash", "bank_name_key", "normalize_bank_name"]
