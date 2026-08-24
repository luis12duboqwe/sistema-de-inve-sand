import asyncio

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth import (
    create_access_token,
    get_current_superuser,
    get_current_user,
    get_current_user_optional,
)
from app.models import User


def _superuser(*, active: bool) -> User:
    return User(
        username="security-super-admin",
        email="security-super-admin@example.com",
        hashed_password="test-hash",
        is_active=active,
        is_superuser=True,
    )


def _protected_app(user: User) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: user

    @app.get("/protected")
    async def protected(current_user: User = Depends(get_current_superuser)):
        return {"username": current_user.username}

    return app


def test_inactive_user_is_rejected_as_unauthorized_during_base_jwt_resolution(db_session):
    user = _superuser(active=False)
    db_session.add(user)
    db_session.commit()
    token = create_access_token({"sub": user.username})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(token=token, db=db_session))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Inactive user"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_optional_auth_treats_inactive_user_as_unauthenticated(db_session):
    user = _superuser(active=False)
    db_session.add(user)
    db_session.commit()
    token = create_access_token({"sub": user.username})

    resolved = asyncio.run(get_current_user_optional(token=token, db=db_session))

    assert resolved is None


def test_inactive_superuser_cannot_use_superuser_dependency():
    client = TestClient(_protected_app(_superuser(active=False)))

    response = client.get("/protected")

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


def test_active_superuser_can_use_superuser_dependency():
    client = TestClient(_protected_app(_superuser(active=True)))

    response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"username": "security-super-admin"}
