from types import SimpleNamespace

import jwt
import pytest
from fastapi import WebSocketException, status

from app.config import settings
from app.routers import websocket as websocket_router


class FakeWebSocket:
    def __init__(self, protocol_header: str = ""):
        self.headers = {"sec-websocket-protocol": protocol_header}
        self.closed = []
        self.receive_calls = 0

    async def receive_text(self):
        self.receive_calls += 1
        raise RuntimeError("client disconnected")

    async def close(self, *, code: int, reason: str):
        self.closed.append((code, reason))


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, result):
        self.result = result

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.result)


class FakeManager:
    def __init__(self):
        self.connected = []
        self.disconnected = []

    async def connect(self, websocket, *, namespace: str, subprotocol: str):
        self.connected.append((websocket, namespace, subprotocol))

    async def disconnect(self, websocket, *, namespace: str):
        self.disconnected.append((websocket, namespace))


def _token(subject: str = "alice") -> str:
    return jwt.encode({"sub": subject}, settings.secret_key, algorithm=settings.algorithm)


def _user(*, active=True, superuser=False, permissions=()):
    role = SimpleNamespace(
        permissions=[SimpleNamespace(slug=slug) for slug in permissions]
    )
    return SimpleNamespace(
        id=1,
        username="alice",
        is_active=active,
        is_superuser=superuser,
        role=role,
    )


def test_extract_subprotocol_token_requires_access_token_protocol_first():
    token = _token()

    assert websocket_router._extract_subprotocol_token(
        FakeWebSocket(f"access_token, {token}")
    ) == token

    for header in ("", token, f"other, {token}", "access_token"):
        with pytest.raises(WebSocketException) as exc_info:
            websocket_router._extract_subprotocol_token(FakeWebSocket(header))
        assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION


def test_user_permission_allows_superuser_and_exact_role_permission():
    assert websocket_router._user_has_permission(
        _user(superuser=True), "photo_requests:list"
    ) is True
    assert websocket_router._user_has_permission(
        _user(permissions=("photo_requests:list",)), "photo_requests:list"
    ) is True
    assert websocket_router._user_has_permission(
        _user(permissions=("orders:view",)), "photo_requests:list"
    ) is False

    no_role = _user()
    no_role.role = None
    assert websocket_router._user_has_permission(no_role, "photo_requests:list") is False


@pytest.mark.asyncio
async def test_get_user_from_ws_accepts_active_authorized_user():
    user = _user(permissions=("photo_requests:list",))
    websocket = FakeWebSocket(f"access_token, {_token()}")

    result = await websocket_router.get_user_from_ws(
        websocket,
        FakeSession(user),
        required_permission="photo_requests:list",
    )

    assert result is user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("db_user", "subject", "permission", "reason"),
    [
        (None, "alice", None, "User not found"),
        (_user(active=False), "alice", None, "Inactive user"),
        (_user(permissions=("orders:view",)), "alice", "photo_requests:list", "Permission denied"),
    ],
)
async def test_get_user_from_ws_rejects_invalid_user_state(db_user, subject, permission, reason):
    websocket = FakeWebSocket(f"access_token, {_token(subject)}")

    with pytest.raises(WebSocketException) as exc_info:
        await websocket_router.get_user_from_ws(
            websocket,
            FakeSession(db_user),
            required_permission=permission,
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    assert exc_info.value.reason == reason


@pytest.mark.asyncio
async def test_get_user_from_ws_rejects_invalid_token_and_empty_subject():
    invalid = FakeWebSocket("access_token, not-a-jwt")
    with pytest.raises(WebSocketException) as exc_info:
        await websocket_router.get_user_from_ws(invalid, FakeSession(_user()))
    assert exc_info.value.reason == "Invalid token"

    empty_subject_token = jwt.encode(
        {"sub": ""}, settings.secret_key, algorithm=settings.algorithm
    )
    empty_subject = FakeWebSocket(f"access_token, {empty_subject_token}")
    with pytest.raises(WebSocketException) as exc_info:
        await websocket_router.get_user_from_ws(empty_subject, FakeSession(_user()))
    assert exc_info.value.reason == "Invalid token payload"


@pytest.mark.asyncio
async def test_photo_request_websocket_connects_then_disconnects_cleanly(monkeypatch):
    manager = FakeManager()
    websocket = FakeWebSocket()

    async def fake_auth(_websocket, _db, *, required_permission=None):
        assert required_permission == "photo_requests:list"
        return _user(permissions=("photo_requests:list",))

    monkeypatch.setattr(websocket_router, "manager", manager)
    monkeypatch.setattr(websocket_router, "get_user_from_ws", fake_auth)

    await websocket_router.websocket_photo_requests(websocket, db=object())

    assert manager.connected == [
        (websocket, "photo-requests", websocket_router.WS_AUTH_PROTOCOL)
    ]
    assert manager.disconnected == [(websocket, "photo-requests")]
    assert websocket.receive_calls == 1


@pytest.mark.asyncio
async def test_photo_request_websocket_closes_policy_violation_and_still_disconnects(monkeypatch):
    manager = FakeManager()
    websocket = FakeWebSocket()

    async def reject(_websocket, _db, *, required_permission=None):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Permission denied",
        )

    monkeypatch.setattr(websocket_router, "manager", manager)
    monkeypatch.setattr(websocket_router, "get_user_from_ws", reject)

    await websocket_router.websocket_photo_requests(websocket, db=object())

    assert manager.connected == []
    assert websocket.closed == [
        (status.WS_1008_POLICY_VIOLATION, "Permission denied")
    ]
    assert manager.disconnected == [(websocket, "photo-requests")]


@pytest.mark.asyncio
async def test_admin_websocket_requires_superuser(monkeypatch):
    manager = FakeManager()
    websocket = FakeWebSocket()

    async def normal_user(_websocket, _db, *, required_permission=None):
        return _user(superuser=False)

    monkeypatch.setattr(websocket_router, "manager", manager)
    monkeypatch.setattr(websocket_router, "get_user_from_ws", normal_user)

    await websocket_router.websocket_admin(websocket, db=object())

    assert manager.connected == []
    assert websocket.closed == [
        (status.WS_1008_POLICY_VIOLATION, "Admin access required")
    ]
    assert manager.disconnected == [(websocket, "admin")]
