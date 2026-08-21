"""Authenticated WebSocket routes for real-time updates.

JWTs are transported through the WebSocket subprotocol handshake rather than the
URL query string so reverse-proxy/access logs do not capture bearer credentials.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocketException, status
from fastapi.websockets import WebSocket
import jwt
from jwt import PyJWTError as JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.utils.websocket_manager import get_connection_manager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])
manager = get_connection_manager()
WS_AUTH_PROTOCOL = "access_token"


def _extract_subprotocol_token(websocket: WebSocket) -> str:
    raw = websocket.headers.get("sec-websocket-protocol", "")
    protocols = [part.strip() for part in raw.split(",") if part.strip()]
    if len(protocols) < 2 or protocols[0] != WS_AUTH_PROTOCOL:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authenticated WebSocket subprotocol required",
        )
    return protocols[1]


def _user_has_permission(user: User, permission_slug: str) -> bool:
    if bool(user.is_superuser):
        return True
    if not user.role:
        return False
    return any(permission.slug == permission_slug for permission in (user.role.permissions or []))


async def get_user_from_ws(
    websocket: WebSocket,
    db: Session,
    *,
    required_permission: Optional[str] = None,
) -> User:
    token = _extract_subprotocol_token(websocket)
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        if not user.is_active:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Inactive user")
        if required_permission and not _user_has_permission(user, required_permission):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Permission denied")
        return user
    except JWTError as exc:
        logger.warning("WebSocket authentication failed")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token") from exc


@router.websocket("/photo-requests")
async def websocket_photo_requests(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """Real-time photo-request events for authorized active staff."""
    try:
        current_user = await get_user_from_ws(
            websocket,
            db,
            required_permission="photo_requests:list",
        )
        await manager.connect(
            websocket,
            namespace="photo-requests",
            subprotocol=WS_AUTH_PROTOCOL,
        )
        logger.info("User %s connected to photo-requests WebSocket", current_user.id)

        while True:
            try:
                await websocket.receive_text()
            except Exception:
                break

    except WebSocketException as exc:
        logger.warning("Photo-request WebSocket rejected: %s", exc.reason)
        try:
            await websocket.close(code=exc.code, reason=exc.reason)
        except Exception:
            pass
    except Exception:
        logger.exception("Unexpected photo-request WebSocket error")
    finally:
        await manager.disconnect(websocket, namespace="photo-requests")


@router.websocket("/admin")
async def websocket_admin(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """Real-time Super Admin events."""
    try:
        current_user = await get_user_from_ws(websocket, db)
        if not bool(current_user.is_superuser):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Admin access required")

        await manager.connect(websocket, namespace="admin", subprotocol=WS_AUTH_PROTOCOL)
        logger.info("Admin %s connected to WebSocket", current_user.id)
        while True:
            try:
                await websocket.receive_text()
            except Exception:
                break
    except WebSocketException as exc:
        try:
            await websocket.close(code=exc.code, reason=exc.reason)
        except Exception:
            pass
    except Exception:
        logger.exception("Unexpected admin WebSocket error")
    finally:
        await manager.disconnect(websocket, namespace="admin")
