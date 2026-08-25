import json
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.models import SalesProfile
from app.routers import channel_integrity


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    responses: list[_FakeResponse] = []
    calls: list[dict[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.__class__.calls.append({"url": url, **kwargs})
        return self.__class__.responses.pop(0)


def _profile(db: Session, slug: str, channel: str, channel_config: dict[str, str]) -> SalesProfile:
    profile = SalesProfile(
        name=f"Profile {slug}",
        slug=slug,
        tipo="bot_ia",
        canales=json.dumps([channel]),
        active=True,
        configuracion=json.dumps(
            {"channel_integrations": {channel: channel_config}}
        ),
    )
    db.add(profile)
    db.commit()
    return profile


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, responses: list[_FakeResponse]) -> None:
    _FakeAsyncClient.responses = list(responses)
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(channel_integrity.httpx, "AsyncClient", _FakeAsyncClient)


@pytest.mark.asyncio
async def test_messenger_basic_read_is_not_enough_without_messaging_permission(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _profile(
        db_session,
        "messenger-probe",
        "messenger",
        {"page_id": "page-123", "page_access_token": "page-token"},
    )
    _install_fake_client(
        monkeypatch,
        [_FakeResponse(200, {"id": "page-123", "name": "Demo"}), _FakeResponse(403)],
    )

    result = await channel_integrity.test_channel_connection_integrity(
        "messenger-probe", "messenger", db_session, None  # type: ignore[arg-type]
    )

    assert result["status"] == "error"
    assert "mensajería" in result["details"]
    assert _FakeAsyncClient.calls[1]["url"].endswith("/page-123/conversations")
    assert _FakeAsyncClient.calls[1]["params"] == {"limit": 1}


@pytest.mark.asyncio
async def test_messenger_connection_succeeds_when_conversations_probe_is_authorized(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _profile(
        db_session,
        "messenger-ok",
        "messenger",
        {"page_id": "page-ok", "page_access_token": "page-token"},
    )
    _install_fake_client(
        monkeypatch,
        [_FakeResponse(200, {"id": "page-ok"}), _FakeResponse(200, {"data": []})],
    )

    result = await channel_integrity.test_channel_connection_integrity(
        "messenger-ok", "facebook", db_session, None  # type: ignore[arg-type]
    )

    assert result["status"] == "success"
    assert result["channel"] == "messenger"
    assert "mensajería verificadas" in result["details"]


@pytest.mark.asyncio
async def test_instagram_probe_resolves_page_and_checks_instagram_conversations(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _profile(
        db_session,
        "instagram-ok",
        "instagram",
        {"instagram_account_id": "ig-456", "page_access_token": "page-token"},
    )
    _install_fake_client(
        monkeypatch,
        [
            _FakeResponse(200, {"id": "ig-456", "username": "demo"}),
            _FakeResponse(200, {"id": "page-456"}),
            _FakeResponse(200, {"data": []}),
        ],
    )

    result = await channel_integrity.test_channel_connection_integrity(
        "instagram-ok", "instagram", db_session, None  # type: ignore[arg-type]
    )

    assert result["status"] == "success"
    assert _FakeAsyncClient.calls[1]["url"].endswith("/me")
    assert _FakeAsyncClient.calls[2]["url"].endswith("/page-456/conversations")
    assert _FakeAsyncClient.calls[2]["params"] == {"platform": "instagram", "limit": 1}


@pytest.mark.asyncio
async def test_instagram_probe_fails_closed_when_page_id_cannot_be_resolved(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _profile(
        db_session,
        "instagram-no-page",
        "instagram",
        {"instagram_account_id": "ig-789", "page_access_token": "page-token"},
    )
    _install_fake_client(
        monkeypatch,
        [_FakeResponse(200, {"id": "ig-789"}), _FakeResponse(200, {})],
    )

    result = await channel_integrity.test_channel_connection_integrity(
        "instagram-no-page", "instagram", db_session, None  # type: ignore[arg-type]
    )

    assert result["status"] == "error"
    assert "Page ID" in result["details"]


@pytest.mark.asyncio
async def test_whatsapp_keeps_non_destructive_identity_probe_only(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _profile(
        db_session,
        "whatsapp-probe",
        "whatsapp",
        {"phone_number_id": "phone-1", "access_token": "wa-token"},
    )
    _install_fake_client(
        monkeypatch,
        [_FakeResponse(200, {"id": "phone-1", "verified_name": "Demo"})],
    )

    result = await channel_integrity.test_channel_connection_integrity(
        "whatsapp-probe", "whatsapp", db_session, None  # type: ignore[arg-type]
    )

    assert result["status"] == "success"
    assert len(_FakeAsyncClient.calls) == 1
