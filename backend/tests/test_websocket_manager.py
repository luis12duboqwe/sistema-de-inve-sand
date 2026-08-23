import json

import pytest

from app.utils.websocket_manager import (
    PhotoRequestEventBroadcaster,
    WebSocketConnectionManager,
)


class FakeSocket:
    def __init__(self, *, fail_send: bool = False):
        self.accepted_subprotocols = []
        self.sent = []
        self.fail_send = fail_send

    async def accept(self, *, subprotocol=None):
        self.accepted_subprotocols.append(subprotocol)

    async def send_text(self, message: str):
        if self.fail_send:
            raise RuntimeError("socket closed")
        self.sent.append(message)


@pytest.mark.asyncio
async def test_broadcaster_delivers_specific_and_global_subscribers_and_can_unsubscribe():
    broadcaster = PhotoRequestEventBroadcaster()
    specific_events = []
    all_events = []

    async def specific(event):
        specific_events.append(event)

    async def global_handler(event):
        all_events.append(event)

    await broadcaster.subscribe("photo_request.created", specific)
    await broadcaster.subscribe_all(global_handler)
    await broadcaster.publish(
        "photo_request.created",
        42,
        {"source": "test"},
        user_id=7,
    )

    assert len(specific_events) == 1
    assert len(all_events) == 1
    assert specific_events[0]["photo_request_id"] == 42
    assert specific_events[0]["payload"] == {"source": "test"}
    assert specific_events[0]["user_id"] == 7
    assert specific_events[0]["timestamp"]

    await broadcaster.unsubscribe("photo_request.created", specific)
    await broadcaster.unsubscribe_all(global_handler)
    await broadcaster.publish("photo_request.created", 43)

    assert len(specific_events) == 1
    assert len(all_events) == 1


@pytest.mark.asyncio
async def test_broadcaster_isolates_failing_subscriber():
    broadcaster = PhotoRequestEventBroadcaster()
    delivered = []

    async def failing(_event):
        raise RuntimeError("boom")

    async def healthy(event):
        delivered.append(event["photo_request_id"])

    await broadcaster.subscribe("event", failing)
    await broadcaster.subscribe("event", healthy)
    await broadcaster.subscribe_all(failing)
    await broadcaster.subscribe_all(healthy)

    await broadcaster.publish("event", 99)

    assert delivered == [99, 99]


@pytest.mark.asyncio
async def test_connection_manager_accepts_tracks_and_disconnects_namespaces():
    manager = WebSocketConnectionManager()
    photo = FakeSocket()
    custom = FakeSocket()

    await manager.connect(photo, namespace="photo-requests", subprotocol="access_token")
    await manager.connect(custom, namespace="custom")

    assert photo.accepted_subprotocols == ["access_token"]
    assert custom.accepted_subprotocols == [None]
    assert manager.get_connection_count("photo-requests") == 1
    assert manager.get_connection_count("custom") == 1
    assert manager.get_connection_count() == 2

    await manager.disconnect(photo, namespace="photo-requests")
    await manager.disconnect(custom, namespace="missing")

    assert manager.get_connection_count("photo-requests") == 0
    assert manager.get_connection_count() == 1


@pytest.mark.asyncio
async def test_broadcast_sends_payload_drops_failed_socket_and_publishes_to_broadcaster():
    manager = WebSocketConnectionManager()
    healthy = FakeSocket()
    failed = FakeSocket(fail_send=True)
    observed = []

    async def observe(event):
        observed.append(event)

    await manager.connect(healthy, namespace="photo-requests")
    await manager.connect(failed, namespace="photo-requests")
    await manager.broadcaster.subscribe_all(observe)

    await manager.broadcast_photo_event(
        "photo_request.completed",
        15,
        {"status": "completed"},
        user_id=3,
    )

    assert manager.get_connection_count("photo-requests") == 1
    assert manager.active_connections["photo-requests"] == [healthy]
    assert len(healthy.sent) == 1

    message = json.loads(healthy.sent[0])
    assert message["event"] == "photo_request.completed"
    assert message["photo_request_id"] == 15
    assert message["payload"] == {"status": "completed"}
    assert message["user_id"] == 3
    assert message["timestamp"]

    assert len(observed) == 1
    assert observed[0]["event_type"] == "photo_request.completed"
    assert observed[0]["photo_request_id"] == 15


@pytest.mark.asyncio
async def test_broadcast_without_connections_still_notifies_in_process_subscribers():
    manager = WebSocketConnectionManager()
    observed = []

    async def observe(event):
        observed.append(event["photo_request_id"])

    await manager.broadcaster.subscribe_all(observe)

    await manager.broadcast_photo_event("photo_request.created", 88, namespace="unknown")

    assert observed == [88]
    assert manager.get_connection_count("unknown") == 0
