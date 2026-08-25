from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Profile


def _create_profile(db_session: Session, *, settings: str | None) -> Profile:
    profile = Profile(
        name="Perfil Legacy",
        slug="perfil-legacy-settings",
        active=True,
        settings=settings,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def test_profile_update_persists_settings(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = _create_profile(db_session, settings='{"theme":"old"}')

    response = client.put(
        f"/api/profiles/{profile.id}",
        json={"settings": '{"theme":"new"}'},
    )

    assert response.status_code == 200, response.text
    assert response.json()["settings"] == '{"theme":"new"}'

    db_session.expire_all()
    stored = db_session.query(Profile).filter(Profile.id == profile.id).one()
    assert stored.settings == '{"theme":"new"}'


def test_profile_update_preserves_settings_when_field_is_omitted(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = _create_profile(db_session, settings='{"theme":"keep"}')

    response = client.put(
        f"/api/profiles/{profile.id}",
        json={"name": "Perfil Renombrado"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Perfil Renombrado"
    assert response.json()["settings"] == '{"theme":"keep"}'

    db_session.expire_all()
    stored = db_session.query(Profile).filter(Profile.id == profile.id).one()
    assert stored.settings == '{"theme":"keep"}'


def test_profile_update_explicit_null_clears_settings(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = _create_profile(db_session, settings='{"theme":"clear-me"}')

    response = client.put(
        f"/api/profiles/{profile.id}",
        json={"settings": None},
    )

    assert response.status_code == 200, response.text
    assert response.json()["settings"] is None

    db_session.expire_all()
    stored = db_session.query(Profile).filter(Profile.id == profile.id).one()
    assert stored.settings is None
