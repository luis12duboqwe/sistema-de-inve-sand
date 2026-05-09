import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def _json_dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def log_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    location_id: Optional[int] = None,
    user: Optional[User] = None,
    before_data: Any = None,
    after_data: Any = None,
    metadata: Any = None,
) -> None:
    user_id = None
    username = None
    if user is not None:
        username = getattr(user, "username", None)
        candidate_user_id = getattr(user, "id", None)
        if candidate_user_id is not None:
            try:
                exists = db.query(User.id).filter(User.id == candidate_user_id).first()
                if exists:
                    user_id = candidate_user_id
            except Exception:
                user_id = None

    db.add(AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        location_id=location_id,
        before_data=_json_dump(before_data),
        after_data=_json_dump(after_data),
        metadata_json=_json_dump(metadata),
    ))