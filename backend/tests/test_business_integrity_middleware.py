from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy.orm import Session

from app.auth import create_access_token
from app.middleware import business_integrity
from app.models import User

from .helpers import seed_location_and_sales_profile


def _force_production_without_photo_service_token(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        type(business_integrity.prod_settings),
        "is_production",
        lambda self: True,
    )
    monkeypatch.setattr(business_integrity.prod_settings, "N8N_AUTH_TOKEN", "")


def test_photo_create_rejects_bogus_bearer_when_service_token_missing(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    _, sales_profile = seed_location_and_sales_profile(db_session)
    _force_production_without_photo_service_token(monkeypatch)

    response = client.post(
        "/api/photo-requests/create",
        headers={"Authorization": "Bearer junk"},
        params={"sales_profile_slug": sales_profile.slug, "channel": "whatsapp"},
        json={
            "customer_id": "50411110000",
            "product_name": "Producto Test",
        },
    )

    assert response.status_code == 503, response.text


def test_photo_create_allows_verified_active_user_when_service_token_missing(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    _, sales_profile = seed_location_and_sales_profile(db_session)
    user = User(
        username="verified-photo-user",
        email="verified-photo-user@test.local",
        hashed_password="unused-in-this-test",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()

    _force_production_without_photo_service_token(monkeypatch)
    token = create_access_token({"sub": user.username})

    response = client.post(
        "/api/photo-requests/create",
        headers={"Authorization": f"Bearer {token}"},
        params={"sales_profile_slug": sales_profile.slug, "channel": "whatsapp"},
        json={
            "customer_id": "50411110001",
            "product_name": "Producto Test",
        },
    )

    assert response.status_code == 200, response.text
