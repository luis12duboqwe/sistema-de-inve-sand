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
    """
    In-memory event broadcaster for photo requests.
    
    In production, replace with Redis/Kafka for distributed systems.
    """
    
    def __init__(self):
        # Map of event_type -> set of subscribed handler functions
        self._subscribers: Dict[str, List[Callable[..., Awaitable[Any]]]] = {}
        self._all_subscribers: List[Callable[..., Awaitable[Any]]] = []
    
    async def subscribe(self, event_type: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}")
    
    async def subscribe_all(self, handler: Callable[..., Awaitable[Any]]) -> None:
        """Subscribe to all events."""
        self._all_subscribers.append(handler)
    
    async def unsubscribe(self, event_type: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Unsubscribe from a specific event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h is not handler
            ]
    
    async def unsubscribe_all(self, handler: Callable[..., Awaitable[Any]]) -> None:
        """Unsubscribe from all events."""
        self._all_subscribers = [h for h in self._all_subscribers if h is not handler]
    
    async def publish(
        self,
        event_type: str,
        photo_request_id: int,
        payload: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> None:
        """Publish an event to all subscribers."""
        event_data: Dict[str, Any] = {
            "event_type": event_type,
            "photo_request_id": photo_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "payload": payload or {}
        }
        
        logger.debug(f"Publishing {event_type} for request {photo_request_id}")
        
        # Notify specific event type subscribers
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    await handler(event_data)
                except Exception as e:
                    logger.error(f"Error in subscriber: {e}")
        
        # Notify all event subscribers
        for handler in self._all_subscribers:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Error in all-event subscriber: {e}")


class WebSocketConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        # Track active connections by namespace
        self.active_connections: Dict[str, List[WebSocket]] = {
            "photo-requests": [],  # Agentes viendo solicitudes
            "admin": [],           # Admin dashboard
            "general": []          # General updates
        }
        self.broadcaster = PhotoRequestEventBroadcaster()
    
    async def connect(self, websocket: WebSocket, namespace: str = "general"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if namespace not in self.active_connections:
            self.active_connections[namespace] = []
        self.active_connections[namespace].append(websocket)
        logger.info(f"Client connected to {namespace}. Total: {len(self.active_connections[namespace])}")
    
    async def disconnect(self, websocket: WebSocket, namespace: str = "general"):
        """Remove a client connection."""
        if namespace in self.active_connections:
            self.active_connections[namespace] = [
                ws for ws in self.active_connections[namespace] if ws is not websocket
            ]
            logger.info(f"Client disconnected from {namespace}. Total: {len(self.active_connections.get(namespace, []))}")
    
    async def broadcast_photo_event(
        self,
        event_type: str,
        photo_request_id: int,
        payload: Optional[Dict[str, Any]] = None,
        namespace: str = "photo-requests",
        user_id: Optional[int] = None
    ) -> None:
        """Broadcast a photo request event to all connected clients."""
        event_data: Dict[str, Any] = {
            "event": event_type,
            "photo_request_id": photo_request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
            "user_id": user_id
        }
        
        message = json.dumps(event_data)
        
        # Broadcast to specific namespace
        if namespace in self.active_connections:
            disconnected: List[WebSocket] = []
            for websocket in self.active_connections[namespace]:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"Error sending to client: {e}")
                    disconnected.append(websocket)
            
            # Remove dead connections
            for ws in disconnected:
                await self.disconnect(ws, namespace)
        
        # Also publish to internal broadcaster for other handlers
        await self.broadcaster.publish(event_type, photo_request_id, payload, user_id)
    
    def get_connection_count(self, namespace: Optional[str] = None) -> int:
        """Get number of active connections."""
        if namespace:
            return len(self.active_connections.get(namespace, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Global instance
_manager: Optional[WebSocketConnectionManager] = None

def get_connection_manager() -> WebSocketConnectionManager:
    """Get or create the connection manager singleton."""
    global _manager
    if _manager is None:  # noqa: SIM102
        _manager = WebSocketConnectionManager()
    return _manager
