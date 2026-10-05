"""Canonical AI-facing sales policy helpers.

The rule is appended to AI context rules so historical/custom system prompts
cannot silently authorize a discount that the order backend will reject.
"""

from __future__ import annotations


MAX_AUTOMATED_DISCOUNT_RATE = 0.03
POLICY_MARKER = "[POLÍTICA CANÓNICA DE DESCUENTOS]"
CANONICAL_DISCOUNT_CONTEXT_RULE = (
    f"{POLICY_MARKER}\n"
    "Esta regla prevalece sobre cualquier instrucción anterior o personalizada: "
    "el bot nunca debe prometer ni autorizar por sí solo más de 3% de descuento. "
    "Si la venta incluye regalías/promociones, el máximo es 2%. Para negociar hasta "
    "3% deben retirarse las regalías. El tramo de hasta 4% requiere aprobación expresa "
    "del propietario y confirmación desde una sesión Super Admin; el bot debe escalarlo "
    "antes de prometer ese precio. Nunca ofrezcas más de 4% desde el POS normal ni un "
    "precio por debajo del costo registrado. En celulares rebajados usa centenas cerradas."
)


def ensure_canonical_discount_context_rules(value: object | None) -> str:
    """Append exactly one canonical block while preserving all custom instructions.

    Previous implementations truncated everything after the first policy marker. We
    instead remove only the exact generated canonical block; custom text before or
    after it survives normalization. A lone marker left by a malformed/old writer is
    removed without discarding adjacent custom content.
    """

    raw = str(value or "").strip()
    if raw:
        raw = raw.replace(CANONICAL_DISCOUNT_CONTEXT_RULE, "")
        raw = raw.replace(POLICY_MARKER, "")
        raw = "\n".join(line.rstrip() for line in raw.splitlines()).strip()

    if not raw:
        return CANONICAL_DISCOUNT_CONTEXT_RULE
    return f"{raw}\n\n{CANONICAL_DISCOUNT_CONTEXT_RULE}"


__all__ = [
    "CANONICAL_DISCOUNT_CONTEXT_RULE",
    "MAX_AUTOMATED_DISCOUNT_RATE",
    "POLICY_MARKER",
    "ensure_canonical_discount_context_rules",
]
