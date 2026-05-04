"""
WebSocket router for real-time photo request updates.

Endpoints:
- ws://localhost:8000/ws/photo-requests - Real-time photo request updates
"""

import logging
from typing import Optional
from fastapi import APIRouter, WebSocketException, status, Depends, Query
from fastapi.websockets import WebSocket
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import User
from app.utils.websocket_manager import get_connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])

manager = get_connection_manager()


async def get_user_from_ws(websocket: WebSocket, token: Optional[str], db: Session) -> User:
    """Authenticate WebSocket connection with JWT token."""
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token required")
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        return user
    except JWTError as e:
        logger.warning(f"WebSocket auth failed: {e}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")


@router.websocket("/photo-requests")
async def websocket_photo_requests(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time photo request updates.
    
    Query params:
    - token: JWT authentication token
    
    Events sent:
    - photo_request.created: New request created
    - photo_request.claimed: Request claimed by agent
    - photo_request.media_uploaded: Photo uploaded
    - photo_request.status_changed: Status changed
    - photo_request.assigned: Assigned to agent
    
    Example client:
    ```js
    const ws = new WebSocket(`ws://localhost:8000/ws/photo-requests?token=${token}`)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log(`${data.event} for request ${data.photo_request_id}`)
    }
    ```
    """
    
    try:
        # Authenticate
        current_user = await get_user_from_ws(websocket, token, db)
        await manager.connect(websocket, namespace="photo-requests")
        
        logger.info(f"User {current_user.id} connected to photo-requests WebSocket")
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received from {current_user.id}: {data}")
                
                # Echo back as confirmation (optional)
                # await websocket.send_text(f"Received: {data}")
                
            except Exception as e:
                logger.warning(f"WebSocket receive error: {e}")
                break
    
    except WebSocketException as e:
        logger.error(f"WebSocket auth error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e))
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, namespace="photo-requests")
    
    finally:
        await manager.disconnect(websocket, namespace="photo-requests")


@router.websocket("/admin")
async def websocket_admin(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for admin dashboard real-time updates."""
    try:
        current_user = await get_user_from_ws(websocket, token, db)
        
        # Check admin permission
        if not bool(current_user.is_superuser):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Admin access required")
        
        await manager.connect(websocket, namespace="admin")
        logger.info(f"Admin {current_user.id} connected")
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Admin {current_user.id}: {data}")
            except Exception as e:
                logger.warning(f"Admin WebSocket error: {e}")
                break
    
    except WebSocketException as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e))
    finally:
        await manager.disconnect(websocket, namespace="admin")
