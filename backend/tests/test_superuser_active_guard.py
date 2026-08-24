from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import get_current_superuser, get_current_user
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
