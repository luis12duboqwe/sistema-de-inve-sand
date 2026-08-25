import json

from app.models import SalesProfile
from app.routers import channel_integrity


class _FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, *, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        assert self._responses, f"Llamada Meta inesperada: {url}"
        return self._responses.pop(0)


def _profile(db_session, channel: str, config: dict, *, slug: str = "meta-test"):
    profile = SalesProfile(
        name="Meta Test",
        slug=slug,
        tipo="bot_ia",
        canales=json.dumps([channel]),
        active=True,
        configuracion=json.dumps(
            {"channel_integrations": {channel: config}}
        ),
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def _install_fake_client(monkeypatch, responses):
    fake = _FakeAsyncClient(responses)
    monkeypatch.setattr(
        channel_integrity.httpx,
        "AsyncClient",
        lambda **kwargs: fake,
    )
    return fake


def test_messenger_rejects_page_token_owned_by_different_page(client, db_session, monkeypatch):
    _profile(
        db_session,
        "messenger",
        {"page_id": "page-configured", "page_access_token": "token"},
    )
    fake = _install_fake_client(
        monkeypatch,
        [_FakeResponse(200, {"id": "page-other", "name": "Other Page"})],
    )

    response = client.post("/api/channels/test-connection/meta-test/messenger")

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Page distinta" in response.json()["details"]
    assert len(fake.calls) == 1
    assert fake.calls[0]["url"].endswith("/me")


def test_messenger_rejects_token_without_messaging_capability(client, db_session, monkeypatch):
    _profile(
        db_session,
        "messenger",
        {"page_id": "page-1", "page_access_token": "token"},
    )
    fake = _install_fake_client(
        monkeypatch,
        [
            _FakeResponse(200, {"id": "page-1", "name": "Store"}),
            _FakeResponse(400, {"error": {"code": 200}}),
        ],
    )

    response = client.post("/api/channels/test-connection/meta-test/messenger")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert "capacidad de mensajería" in payload["details"]
    assert fake.calls[1]["url"].endswith("/page-1/conversations")
    assert fake.calls[1]["params"] == {"limit": "1"}


def test_facebook_alias_verifies_messenger_capability(client, db_session, monkeypatch):
    _profile(
        db_session,
        "messenger",
        {"page_id": "page-1", "page_access_token": "token"},
    )
    fake = _install_fake_client(
        monkeypatch,
        [
            _FakeResponse(200, {"id": "page-1", "name": "Store"}),
            _FakeResponse(200, {"data": []}),
        ],
    )

    response = client.post("/api/channels/test-connection/meta-test/facebook")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["channel"] == "messenger"
    assert "capacidad de mensajería verificadas" in payload["details"]
    assert len(fake.calls) == 2


def test_instagram_rejects_page_without_linked_professional_account(client, db_session, monkeypatch):
    _profile(
        db_session,
        "instagram",
        {"instagram_account_id": "ig-1", "page_access_token": "token"},
    )
    fake = _install_fake_client(
        monkeypatch,
        [_FakeResponse(200, {"id": "page-1", "name": "Store"})],
    )

    response = client.post("/api/channels/test-connection/meta-test/instagram")

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "no tiene una cuenta profesional" in response.json()["details"]
    assert len(fake.calls) == 1


def test_instagram_rejects_different_linked_account(client, db_session, monkeypatch):
    _profile(
        db_session,
        "instagram",
        {"instagram_account_id": "ig-configured", "page_access_token": "token"},
    )
    _install_fake_client(
        monkeypatch,
        [
            _FakeResponse(
                200,
                {
                    "id": "page-1",
                    "name": "Store",
                    "instagram_business_account": {"id": "ig-other"},
                },
            )
        ],
    )

    response = client.post("/api/channels/test-connection/meta-test/instagram")

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "no coincide" in response.json()["details"]


def test_instagram_verifies_link_and_messaging_capability(client, db_session, monkeypatch):
    _profile(
        db_session,
        "instagram",
        {"instagram_account_id": "ig-1", "page_access_token": "token"},
    )
    fake = _install_fake_client(
        monkeypatch,
        [
            _FakeResponse(
                200,
                {
                    "id": "page-1",
                    "name": "Store",
                    "instagram_business_account": {"id": "ig-1"},
                },
            ),
            _FakeResponse(200, {"data": []}),
        ],
    )

    response = client.post("/api/channels/test-connection/meta-test/instagram")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "capacidad de mensajería verificadas" in payload["details"]
    assert fake.calls[0]["url"].endswith("/me")
    assert fake.calls[0]["params"] == {
        "fields": "id,name,instagram_business_account"
    }
    assert fake.calls[1]["url"].endswith("/page-1/conversations")
    assert fake.calls[1]["params"] == {"platform": "instagram", "limit": "1"}


def test_whatsapp_identity_probe_remains_non_destructive(client, db_session, monkeypatch):
    _profile(
        db_session,
        "whatsapp",
        {"phone_number_id": "phone-1", "access_token": "token"},
    )
    fake = _install_fake_client(
        monkeypatch,
        [
            _FakeResponse(
                200,
                {
                    "id": "phone-1",
                    "display_phone_number": "+50499990000",
                    "verified_name": "Store",
                },
            )
        ],
    )

    response = client.post("/api/channels/test-connection/meta-test/whatsapp")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "Identidad de WhatsApp verificada" in payload["details"]
    assert len(fake.calls) == 1
    assert fake.calls[0]["url"].endswith("/phone-1")
