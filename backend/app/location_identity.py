"""Stable location-name identity shared by model writes and migrations."""

import hashlib
import unicodedata


_UNSAFE_UNICODE_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})

# Keep the same explicit safety boundary used by canonical bank identities.
# Python's Unicode database can lag newer Format additions, so these ranges
# supplement ``unicodedata.category``.
_UNICODE17_FORMAT_RANGES: tuple[tuple[int, int], ...] = (
    (0x00AD, 0x00AD),
    (0x0600, 0x0605),
    (0x061C, 0x061C),
    (0x06DD, 0x06DD),
    (0x070F, 0x070F),
    (0x0890, 0x0891),
    (0x08E2, 0x08E2),
    (0x180E, 0x180E),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x2064),
    (0x2066, 0x206F),
    (0xFEFF, 0xFEFF),
    (0xFFF9, 0xFFFB),
    (0x110BD, 0x110BD),
    (0x110CD, 0x110CD),
    (0x13430, 0x1343F),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0001, 0xE0001),
    (0xE0020, 0xE007F),
)

_DEFAULT_IGNORABLE_RANGES: tuple[tuple[int, int], ...] = (
    (0x00AD, 0x00AD),
    (0x034F, 0x034F),
    (0x061C, 0x061C),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)


def _in_ranges(codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def _assert_safe_unicode(value: str) -> None:
    if any(
        unicodedata.category(char) in _UNSAFE_UNICODE_CATEGORIES
        or _in_ranges(ord(char), _UNICODE17_FORMAT_RANGES)
        or _in_ranges(ord(char), _DEFAULT_IGNORABLE_RANGES)
        for char in value
    ):
        raise ValueError(
            "El nombre de la ubicación contiene caracteres Unicode no permitidos"
        )


def normalize_location_name(name: str) -> str:
    """Return the trimmed display name accepted by location write paths."""
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("El nombre de la ubicación no puede estar vacío")
    _assert_safe_unicode(normalized)
    return normalized


def location_name_key(name: str) -> str:
    """Return a deterministic Unicode-aware logical location identity."""
    display_name = normalize_location_name(name)
    compatibility_normalized = unicodedata.normalize("NFKC", display_name).strip()
    _assert_safe_unicode(compatibility_normalized)
    folded = compatibility_normalized.casefold()
    canonical = unicodedata.normalize("NFKC", folded).strip()
    _assert_safe_unicode(canonical)
    return canonical


def location_name_hash(name: str) -> str:
    """Return an index-safe digest of the complete canonical location identity."""
    return hashlib.sha256(location_name_key(name).encode("utf-8")).hexdigest()


__all__ = ["normalize_location_name", "location_name_hash", "location_name_key"]
