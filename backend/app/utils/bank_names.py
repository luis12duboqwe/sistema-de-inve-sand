"""Canonical bank-name normalization shared by writes and schema migrations."""

import hashlib
import unicodedata


def normalize_bank_name(name: str) -> str:
    """Return the display name stored by canonical financing write paths."""
    normalized = name.strip()
    if len(normalized) < 2:
        raise ValueError("El nombre del banco debe tener al menos 2 caracteres")
    return normalized


def bank_name_key(name: str) -> str:
    """Return the stable Unicode-aware logical identity for a bank name."""
    display_name = normalize_bank_name(name)
    # Compatibility normalization must happen before folding so characters that
    # normalize into uppercase letters are folded too. Normalize once more after
    # folding to keep any newly introduced combining sequence canonical.
    compatibility_normalized = unicodedata.normalize("NFKC", display_name)
    return unicodedata.normalize("NFKC", compatibility_normalized.casefold())


def bank_name_hash(name: str) -> str:
    """Return an index-safe digest of the full canonical bank identity."""
    return hashlib.sha256(bank_name_key(name).encode("utf-8")).hexdigest()


__all__ = ["bank_name_hash", "bank_name_key", "normalize_bank_name"]
