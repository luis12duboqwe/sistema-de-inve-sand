"""Canonical bank-name normalization shared by writes and schema migrations."""


def normalize_bank_name(name: str) -> str:
    """Return the display name stored by canonical financing write paths."""
    normalized = name.strip()
    if len(normalized) < 2:
        raise ValueError("El nombre del banco debe tener al menos 2 caracteres")
    return normalized


def bank_name_key(name: str) -> str:
    """Return the stable uniqueness key for a bank display name."""
    return normalize_bank_name(name).casefold()


__all__ = ["bank_name_key", "normalize_bank_name"]