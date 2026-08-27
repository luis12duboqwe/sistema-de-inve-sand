"""Literal SQL-LIKE helpers for AI context retrieval."""

from __future__ import annotations

from typing import Any, Iterable, List


LIKE_ESCAPE = "\\"
MAX_AI_CONTEXT_SQL_KEYWORDS = 6


def escape_like_literal(value: str) -> str:
    """Escape SQL LIKE metacharacters while preserving literal user text."""
    return (
        value.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def bound_ai_context_sql_keywords(values: Iterable[str]) -> List[str]:
    """Bound only terms that expand SQL predicates; preserve the source message."""
    return list(values)[:MAX_AI_CONTEXT_SQL_KEYWORDS]


def ilike_contains_literal(column: Any, value: str):
    """Build a case-insensitive contains predicate with literal LIKE semantics."""
    escaped = escape_like_literal(value)
    return column.ilike(f"%{escaped}%", escape=LIKE_ESCAPE)


__all__ = [
    "LIKE_ESCAPE",
    "MAX_AI_CONTEXT_SQL_KEYWORDS",
    "bound_ai_context_sql_keywords",
    "escape_like_literal",
    "ilike_contains_literal",
]
