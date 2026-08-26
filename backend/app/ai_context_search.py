"""Literal SQL-LIKE helpers for AI context retrieval."""

from __future__ import annotations

from typing import Any


LIKE_ESCAPE = "\\"


def escape_like_literal(value: str) -> str:
    """Escape SQL LIKE metacharacters while preserving literal user text."""
    return (
        value.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def ilike_contains_literal(column: Any, value: str):
    """Build a case-insensitive contains predicate with literal LIKE semantics."""
    escaped = escape_like_literal(value)
    return column.ilike(f"%{escaped}%", escape=LIKE_ESCAPE)


__all__ = ["LIKE_ESCAPE", "escape_like_literal", "ilike_contains_literal"]
