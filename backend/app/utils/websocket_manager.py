"""
WebSocket event broadcaster for real-time synchronization across clients.

Manages photo request updates, claims, uploads, and status changes.
Uses in-memory broadcast for single-server setups; scalable with Redis/Kafka.
"""

import json
import logging
from typing import Callable, Dict, List, Optional, Any, Awaitable
from datetime import datetime, timezone
from fastapi import WebSocket
from enum import Enum

logger = logging.getLogger(__name__)


class PhotoRequestEventType(str, Enum):
    """Event types for photo request updates."""
    CREATED = "photo_request.created"
    CLAIMED = "photo_request.claimed"
    MEDIA_UPLOADED = "photo_request.media_uploaded"
    STATUS_CHANGED = "photo_request.status_changed"
    ASSIGNED = "photo_request.assigned"
    DECLINED = "photo_request.declined"
    COMPLETED = "photo_request.completed"
    NOTIFICATION_SENT = "photo_request.notification_sent"


class PhotoRequestEventBroadcaster:
    """In-memory event broadcaster for photo requests."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[..., Awaitable[Any]]]] = {}
        self._all_subscribers: List[Callable[..., Awaitable[Any]]] = []

    async def subscribe(self, event_type: str, handler: Callable[..., Awaitable[Any]]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed to %s", event_type)

    async def subscribe_all(self, handler: Callable[..., Awaitable[Any]]) -> None:
        self._all_subscribers.append(handler)

    async def unsubscribe(self, event_type: str, handler: Callable[..., Awaitable[Any]]) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [h for h in self._subscribers[event_type] if h is not handler]

    async def unsubscribe_all(self, handler: Callable[..., Awaitable[Any]]) -> None:
        self._all_subscribers = [h for h in self._all_subscribers if h is not handler]

    async def publish(
        self,
        event_type: str,
        photo_request_id: int,
        payload: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> None:
        event_data: Dict[str, Any] = {
            "event_type": event_type,
            "photo_request_id": photo_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "payload": payload or {},
        }

        logger.debug("Publishing %s for request %s", event_type, photo_request_id)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    await handler(event_data)
                except Exception:
                    logger.exception("Error in websocket subscriber")

        for handler in self._all_subscribers:
            try:
                await handler(event_data)
            except Exception:
                logger.exception("Error in websocket all-event subscriber")


class WebSocketConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "photo-requests": [],
            "admin": [],
            "general": [],
        }
        self.broadcaster = PhotoRequestEventBroadcaster()

    async def connect(
        self,
        websocket: WebSocket,
        namespace: str = "general",
        *,
        subprotocol: str | None = None,
    ):
        """Accept a new WebSocket connection after the caller authenticated it."""
        await websocket.accept(subprotocol=subprotocol)
        if namespace not in self.active_connections:
            self.active_connections[namespace] = []
        self.active_connections[namespace].append(websocket)
        logger.info("Client connected to %s. Total: %s", namespace, len(self.active_connections[namespace]))

    async def disconnect(self, websocket: WebSocket, namespace: str = "general"):
        if namespace in self.active_connections:
            self.active_connections[namespace] = [
                ws for ws in self.active_connections[namespace] if ws is not websocket
            ]
            logger.info("Client disconnected from %s. Total: %s", namespace, len(self.active_connections.get(namespace, [])))

    async def broadcast_photo_event(
        self,
        event_type: str,
        photo_request_id: int,
        payload: Optional[Dict[str, Any]] = None,
        namespace: str = "photo-requests",
        user_id: Optional[int] = None,
    ) -> None:
        event_data: Dict[str, Any] = {
            "event": event_type,
            "photo_request_id": photo_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
            "user_id": user_id,
        }
        message = json.dumps(event_data)

        if namespace in self.active_connections:
            disconnected: List[WebSocket] = []
            for websocket in self.active_connections[namespace]:
                try:
                    await websocket.send_text(message)
                except Exception:
                    logger.warning("Error sending websocket event; dropping client")
                    disconnected.append(websocket)
            for ws in disconnected:
                await self.disconnect(ws, namespace)

        await self.broadcaster.publish(event_type, photo_request_id, payload, user_id)

    def get_connection_count(self, namespace: Optional[str] = None) -> int:
        if namespace:
            return len(self.active_connections.get(namespace, []))
        return sum(len(conns) for conns in self.active_connections.values())


_manager: Optional[WebSocketConnectionManager] = None


def get_connection_manager() -> WebSocketConnectionManager:
    global _manager
    if _manager is None:
        _manager = WebSocketConnectionManager()
    return _manager
