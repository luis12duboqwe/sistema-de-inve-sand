"""Transactional idempotency for business mutations.

Call claim_business_request before the business write; store the response before
the SAME commit. PostgreSQL's unique PK makes concurrent identical requests
wait for the first commit. No second sale/stock mutation is ever performed.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import BusinessRequestKey


_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{12,128}$")


@dataclass
class IdempotencyClaim:
    entry: BusinessRequestKey | None
    replay: dict[str, Any] | None = None


def claim_business_request(
    db: Session,
    *,
    key: str | None,
    identity_id: int,
    endpoint: str,
    payload: dict[str, Any],
) -> IdempotencyClaim:
    if key is None:
        return IdempotencyClaim(entry=None)
    if not _KEY_RE.fullmatch(key):
        raise HTTPException(status_code=400, detail="Idempotency-Key debe tener 12-128 caracteres alfanuméricos/guion")

    key_digest = hashlib.sha256(f"{identity_id}:{endpoint}:{key}".encode()).hexdigest()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload_digest = hashlib.sha256(canonical.encode()).hexdigest()

    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = postgres_insert(BusinessRequestKey)
    elif dialect == "sqlite":
        statement = sqlite_insert(BusinessRequestKey)
    else:
        raise HTTPException(status_code=503, detail="Idempotencia requiere PostgreSQL o SQLite")

    result = db.execute(
        statement.values(key_digest=key_digest, payload_digest=payload_digest)
        .on_conflict_do_nothing(index_elements=["key_digest"])
    )
    # With PostgreSQL READ COMMITTED, a second concurrent INSERT waits for
    # the first commit; afterwards it selects the fully saved response.
    entry = db.query(BusinessRequestKey).filter(
        BusinessRequestKey.key_digest == key_digest
    ).with_for_update().one()
    if entry.payload_digest != payload_digest:
        raise HTTPException(status_code=409, detail="Idempotency-Key reutilizada con datos distintos")
    if result.rowcount == 0:
        if not entry.response_json:
            raise HTTPException(status_code=409, detail="Operación idéntica todavía en proceso")
        return IdempotencyClaim(entry=None, replay=json.loads(entry.response_json))
    return IdempotencyClaim(entry=entry)


def save_business_response(claim: IdempotencyClaim, response: dict[str, Any]) -> None:
    if claim.entry is not None:
        claim.entry.response_json = json.dumps(response, ensure_ascii=False, sort_keys=True)
