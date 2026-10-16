import asyncio
import jwt
import pytest
from fastapi import HTTPException

from app.auth import create_user_access_token, get_current_user, get_password_hash
from app.config import settings
from app.models import User


def _user(username: str) -> User:
    return User(
        username=username,
        email=username + "@example.invalid",
        hashed_password=get_password_hash("temporary-strong-password-1"),
        is_active=True,
        is_superuser=False,
    )


def test_password_change_revokes_prior_jwt_and_new_login_works(db_session):
    user = _user("pwd-revoke")
    db_session.add(user)
    db_session.commit()
    old = create_user_access_token(user)
    assert asyncio.run(get_current_user(token=old, db=db_session)).id == user.id

    user.hashed_password = get_password_hash("temporary-strong-password-2")
    db_session.commit()
    db_session.expire_all()
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_user(token=old, db=db_session))
    assert error.value.status_code == 401

    refreshed = db_session.get(User, user.id)
    new = create_user_access_token(refreshed)
    assert asyncio.run(get_current_user(token=new, db=db_session)).id == user.id


def test_username_reuse_does_not_transfer_session_to_different_user(db_session):
    previous = _user("reused")
    db_session.add(previous)
    db_session.commit()
    stolen = create_user_access_token(previous)
    old_id = previous.id
    previous.username = "renamed-old-user"
    previous.email = "renamed-old-user@example.invalid"
    db_session.flush()
    another = _user("reused")
    db_session.add(another)
    db_session.commit()
    assert another.id != old_id
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_user(token=stolen, db=db_session))
    assert error.value.status_code == 401


def test_legacy_username_only_jwt_is_rejected(db_session):
    user = _user("legacy-revocation")
    db_session.add(user)
    db_session.commit()
    old = jwt.encode({"sub": user.username}, settings.secret_key, algorithm=settings.algorithm)
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_user(token=old, db=db_session))
    assert error.value.status_code == 401


def test_password_update_endpoint_revokes_previous_bearer(client, db_session):
    from app.auth import get_current_user, get_current_active_user
    from app.main import app

    user = _user("password-endpoint")
    db_session.add(user)
    db_session.commit()
    old = create_user_access_token(user)
    previous_current_user = app.dependency_overrides.pop(get_current_user, None)
    previous_active_user = app.dependency_overrides.pop(get_current_active_user, None)
    try:
        first = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"})
        assert first.status_code == 200, first.text
        updated = client.put(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {old}"},
            json={"password": "AnotherStrongSecret!2026"},
        )
        assert updated.status_code == 200, updated.text

        rejected = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old}"})
        assert rejected.status_code == 401
        db_session.expire_all()
        fresh = create_user_access_token(db_session.get(User, user.id))
        accepted = client.get("/api/auth/me", headers={"Authorization": f"Bearer {fresh}"})
        assert accepted.status_code == 200, accepted.text
    finally:
        if previous_current_user is not None:
            app.dependency_overrides[get_current_user] = previous_current_user
        if previous_active_user is not None:
            app.dependency_overrides[get_current_active_user] = previous_active_user
