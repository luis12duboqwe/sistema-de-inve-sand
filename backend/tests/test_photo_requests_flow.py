# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportGeneralTypeIssues=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false

from __future__ import annotations

import json
from typing import Any, TypedDict

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import PhotoRequest, PhotoRequestMediaItem, SalesProfile, User
from app.routers import photo_requests as photo_requests_router
from app.utils.photo_detection import BOT_PHOTO_RESPONSE_TEMPLATES, detect_photo_request

from .helpers import seed_location_and_sales_profile


class _MetaResponse:
    def __init__(self, status_code: int = 200, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text


class _DummyAsyncClient:
    def __init__(self, calls: list[dict[str, Any]], *args: Any, **kwargs: Any) -> None:
        self.calls = calls

    async def __aenter__(self) -> "_DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> _MetaResponse:
        self.calls.append({"url": url, **kwargs})
        return _MetaResponse(200, "ok")


class _AIHandlePayload(TypedDict):
    sales_profile_slug: str
    customer_phone: str
    customer_name: str
    message_content: str


def _seed_active_user(db_session: Session) -> User:
    user = User(
        username="photo-agent",
        email="photo-agent@test.local",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_sales_profile_with_whatsapp(db_session: Session) -> SalesProfile:
    _, sales_profile = seed_location_and_sales_profile(db_session)
    sales_profile.configuracion = json.dumps(
        {
            "channel_integrations": {
                "whatsapp": {
                    "access_token": "token-test",
                    "phone_number_id": "123456",
                }
            }
        }
    )
    sales_profile.canales = json.dumps(["whatsapp"])
    db_session.add(sales_profile)
    db_session.commit()
    db_session.refresh(sales_profile)
    return sales_profile


def test_detect_photo_request_patterns() -> None:
    assert detect_photo_request("Quiero ver fotos del iPhone 15")
    assert detect_photo_request("Muestrame imagenes en gris")
    assert detect_photo_request("Can I see photos of the black color?")
    assert not detect_photo_request("Cual es el precio en efectivo?")


def test_photo_request_full_flow_create_upload_send(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_active_user(db_session)
    sales_profile = _seed_sales_profile_with_whatsapp(db_session)

    create_response = client.post(
        "/api/photo-requests/create",
        json={
            "customer_id": "50488889999",
            "product_name": "iPhone 15 Pro",
            "color_requested": "gris",
        },
        params={
            "sales_profile_slug": sales_profile.slug,
            "channel": "whatsapp",
            "customer_name": "Cliente QA",
        },
    )

    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    request_id = int(created["id"])
    assert created["status"] == "pending"

    upload_response = client.post(
        f"/api/photo-requests/{request_id}/media",
        json={
            "media_url": "https://cdn.example.com/iphone15-gris.jpg",
            "media_type": "photo",
        },
    )
    assert upload_response.status_code == 200, upload_response.text

    send_calls: list[dict[str, Any]] = []

    def _async_client_factory(*args: Any, **kwargs: Any) -> _DummyAsyncClient:
        return _DummyAsyncClient(send_calls, *args, **kwargs)

    monkeypatch.setattr(photo_requests_router.httpx, "AsyncClient", _async_client_factory)

    send_response = client.post(f"/api/photo-requests/{request_id}/send-to-customer")
    assert send_response.status_code == 200, send_response.text

    send_payload = send_response.json()
    assert send_payload["status"] == "success"
    assert send_payload["photo_request_id"] == request_id
    assert len(send_calls) >= 2  # al menos imagen + texto

    request_row = db_session.query(PhotoRequest).filter(PhotoRequest.id == request_id).first()
    assert request_row is not None
    assert request_row.status == "completed"
    assert request_row.resolved_at is not None

    media_rows = db_session.query(PhotoRequestMediaItem).filter(PhotoRequestMediaItem.photo_request_id == request_id).all()
    assert len(media_rows) == 1
    assert media_rows[0].sent_to_customer_at is not None


def test_photo_request_does_not_count_email_when_smtp_unconfigured(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(photo_requests_router.prod_settings, "SMTP_HOST", "")
    monkeypatch.setattr(photo_requests_router.prod_settings, "SMTP_USER", "")
    monkeypatch.setattr(photo_requests_router.prod_settings, "SMTP_FROM", "")

    _seed_active_user(db_session)
    sales_profile = _seed_sales_profile_with_whatsapp(db_session)

    create_response = client.post(
        "/api/photo-requests/create",
        json={
            "customer_id": "50422223333",
            "product_name": "Pixel 9",
            "color_requested": "negro",
        },
        params={
            "sales_profile_slug": sales_profile.slug,
            "channel": "whatsapp",
            "customer_name": "Cliente sin SMTP",
        },
    )

    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    assert created["assigned_to_user_id"] is not None
    assert created["claimed_at"] is None
    assert created["last_notified_at"] is None
    assert created["notification_count"] == 0


def test_send_photos_converts_local_media_url_to_public_absolute_url(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_active_user(db_session)
    sales_profile = _seed_sales_profile_with_whatsapp(db_session)

    create_response = client.post(
        "/api/photo-requests/create",
        json={
            "customer_id": "50455556666",
            "product_name": "iPhone 16",
            "color_requested": "blanco",
        },
        params={
            "sales_profile_slug": sales_profile.slug,
            "channel": "whatsapp",
            "customer_name": "Cliente URL local",
        },
    )
    assert create_response.status_code == 200, create_response.text
    request_id = int(create_response.json()["id"])

    upload_response = client.post(
        f"/api/photo-requests/{request_id}/media",
        json={
            "media_url": "/uploads/requests/1/foto.jpg",
            "media_type": "photo",
        },
    )
    assert upload_response.status_code == 200, upload_response.text

    send_calls: list[dict[str, Any]] = []

    def _async_client_factory(*args: Any, **kwargs: Any) -> _DummyAsyncClient:
        return _DummyAsyncClient(send_calls, *args, **kwargs)

    monkeypatch.setattr(photo_requests_router.httpx, "AsyncClient", _async_client_factory)

    send_response = client.post(f"/api/photo-requests/{request_id}/send-to-customer")
    assert send_response.status_code == 200, send_response.text
    media_payload = send_calls[0]["json"]
    assert media_payload["image"]["link"].startswith("http://testserver/uploads/requests/1/foto.jpg")


def test_photo_request_pending_list_includes_claimed_and_awaiting_upload(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_active_user(db_session)
    sales_profile = _seed_sales_profile_with_whatsapp(db_session)

    create_response = client.post(
        "/api/photo-requests/create",
        json={
            "customer_id": "50411112222",
            "product_name": "Galaxy S24",
            "color_requested": "negro",
        },
        params={
            "sales_profile_slug": sales_profile.slug,
            "channel": "whatsapp",
            "customer_name": "Cliente estados",
        },
    )
    assert create_response.status_code == 200, create_response.text
    request_id = int(create_response.json()["id"])

    claim_response = client.post(f"/api/photo-requests/{request_id}/claim")
    assert claim_response.status_code == 200, claim_response.text
    assert claim_response.json()["status"] == "claimed"

    pending_response = client.get("/api/photo-requests/pending", params={"assigned_to_me": True})
    assert pending_response.status_code == 200, pending_response.text
    pending_ids = {int(item["id"]) for item in pending_response.json()}
    assert request_id in pending_ids

    upload_response = client.post(
        f"/api/photo-requests/{request_id}/media",
        json={
            "media_url": "https://cdn.example.com/galaxy-s24-negro.jpg",
            "media_type": "photo",
        },
    )
    assert upload_response.status_code == 200, upload_response.text

    pending_after_upload = client.get("/api/photo-requests/pending", params={"assigned_to_me": True})
    assert pending_after_upload.status_code == 200, pending_after_upload.text
    pending_after_upload_ids = {int(item["id"]) for item in pending_after_upload.json()}
    assert request_id in pending_after_upload_ids


def test_send_photos_preserves_http_exception_status_codes(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_active_user(db_session)
    sales_profile = _seed_sales_profile_with_whatsapp(db_session)

    create_response = client.post(
        "/api/photo-requests/create",
        json={
            "customer_id": "50433334444",
            "product_name": "iPhone 14",
            "color_requested": "azul",
        },
        params={
            "sales_profile_slug": sales_profile.slug,
            "channel": "telegram",
            "customer_name": "Cliente canal invalido",
        },
    )
    assert create_response.status_code == 200, create_response.text
    request_id = int(create_response.json()["id"])

    upload_response = client.post(
        f"/api/photo-requests/{request_id}/media",
        json={
            "media_url": "https://cdn.example.com/iphone14-azul.jpg",
            "media_type": "photo",
        },
    )
    assert upload_response.status_code == 200, upload_response.text

    request_row = db_session.query(PhotoRequest).filter(PhotoRequest.id == request_id).first()
    assert request_row is not None
    request_row.channel = "telegram"
    db_session.add(request_row)
    db_session.commit()

    monkeypatch.setattr(photo_requests_router, "_resolve_request_channel", lambda _request, _profile: "telegram")

    send_response = client.post(f"/api/photo-requests/{request_id}/send-to-customer")
    assert send_response.status_code == 400, send_response.text
    assert "Canal no soportado" in send_response.json()["detail"]


def test_ai_handle_message_creates_photo_request_when_customer_asks_for_photos(
    client: TestClient,
    db_session: Session,
) -> None:
    _seed_active_user(db_session)
    sales_profile = _seed_sales_profile_with_whatsapp(db_session)

    payload: _AIHandlePayload = {
        "sales_profile_slug": str(sales_profile.slug),
        "customer_phone": "50477778888",
        "customer_name": "Cliente IA",
        "message_content": "Quiero ver fotos del iPhone 15 en gris",
    }

    response = client.post("/api/ai/handle-message", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["reply"] in BOT_PHOTO_RESPONSE_TEMPLATES
    assert data["model"] == "photo-handoff"

    created_request = (
        db_session.query(PhotoRequest)
        .filter(PhotoRequest.customer_id == "50477778888")
        .order_by(PhotoRequest.id.desc())
        .first()
    )
    assert created_request is not None
    assert created_request.status == "pending"
    assert created_request.sales_profile_id == sales_profile.id
    assert created_request.color_requested == "gris"
