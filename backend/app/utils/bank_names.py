"""Canonical bank-name normalization shared by writes and schema migrations."""

import hashlib
import unicodedata


_UNSAFE_UNICODE_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})

# Unicode 17.0, DerivedGeneralCategory.txt: General_Category=Format (Cf).
# Python 3.11 ships an older Unicode database, so newer format controls such as
# Egyptian Hieroglyph controls must be recognized independently of
# ``unicodedata.category``.
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

# Unicode 17.0, DerivedCoreProperties.txt: Default_Ignorable_Code_Point.
# Keep this explicit rather than rejecting every Mn/Lo code point: ordinary
# combining accents are valid bank-name text, while these specific characters
# can disappear in rendering and create visually deceptive identities.
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


def _is_unicode17_format(char: str) -> bool:
    return _in_ranges(ord(char), _UNICODE17_FORMAT_RANGES)


def _is_default_ignorable(char: str) -> bool:
    return _in_ranges(ord(char), _DEFAULT_IGNORABLE_RANGES)


def _assert_safe_unicode(value: str) -> None:
    if any(
        unicodedata.category(char) in _UNSAFE_UNICODE_CATEGORIES
        or _is_unicode17_format(char)
        or _is_default_ignorable(char)
        for char in value
    ):
        raise ValueError("El nombre del banco contiene caracteres Unicode no permitidos")


def normalize_bank_name(name: str) -> str:
    """Return the display name stored by canonical financing write paths."""
    normalized = name.strip()
    if len(normalized) < 2:
        raise ValueError("El nombre del banco debe tener al menos 2 caracteres")
    _assert_safe_unicode(normalized)
    return normalized


def bank_name_key(name: str) -> str:
    """Return the stable Unicode-aware logical identity for a bank name."""
    display_name = normalize_bank_name(name)
    # Compatibility normalization can itself introduce edge whitespace or map a
    # compatibility character into an unsafe code point, so validate each stage.
    compatibility_normalized = unicodedata.normalize("NFKC", display_name).strip()
    _assert_safe_unicode(compatibility_normalized)
    folded = compatibility_normalized.casefold()
    canonical = unicodedata.normalize("NFKC", folded).strip()
    _assert_safe_unicode(canonical)
    return canonical


def bank_name_hash(name: str) -> str:
    """Return an index-safe digest of the full canonical bank identity."""
    return hashlib.sha256(bank_name_key(name).encode("utf-8")).hexdigest()


__all__ = ["bank_name_hash", "bank_name_key", "normalize_bank_name"]
