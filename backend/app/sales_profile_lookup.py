"""Canonical runtime lookup helpers for V2 sales-profile slugs."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import SalesProfile
from app.sales_profile_identity import sales_profile_slug_hash


def find_sales_profile_by_slug(
    db: Session,
    slug: str,
    *,
    active: Optional[bool] = None,
) -> Optional[SalesProfile]:
    """Resolve one V2 sales profile using the database-enforced logical slug identity."""
    try:
        digest = sales_profile_slug_hash(slug)
    except ValueError:
        return None

    query = db.query(SalesProfile).filter(SalesProfile.slug_key_hash == digest)
    if active is not None:
        query = query.filter(SalesProfile.active == active)
    return query.first()


__all__ = ["find_sales_profile_by_slug"]
