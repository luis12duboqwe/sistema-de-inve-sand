import threading
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Permission, Role, SystemConfig, User
from app.routers import auth_setup_integrity
from app.schemas import UserCreate


SETUP_KEY = "initial_admin_setup"


def _request(username: str) -> UserCreate:
    return UserCreate(
        username=username,
        email=f"{username}@example.com",
        full_name=f"Initial {username}",
        password="StrongSetup!123",
    )


def test_openapi_exposes_one_canonical_initial_setup_handler(
    client: TestClient,
) -> None:
    setup_routes = [
        route
        for route in client.app.routes
        if getattr(route, "path", None) == "/api/auth/setup"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]

    assert len(setup_routes) == 1
    assert setup_routes[0].endpoint is auth_setup_integrity.setup_initial_admin_integrity

    schema_response = client.get("/openapi.json")
    assert schema_response.status_code == 200, schema_response.text
    setup_operation = schema_response.json()["paths"]["/api/auth/setup"]["post"]
    assert setup_operation["operationId"].startswith("setup_initial_admin_integrity_")


def test_failed_initial_setup_rolls_back_claim_and_allows_retry(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_hash = auth_setup_integrity.get_password_hash

    def fail_hash(_: str) -> str:
        raise RuntimeError("simulated hashing failure")

    monkeypatch.setattr(auth_setup_integrity, "get_password_hash", fail_hash)

    with pytest.raises(RuntimeError, match="simulated hashing failure"):
        auth_setup_integrity.setup_initial_admin_integrity(
            _request("firstadmin"),
            db_session,
        )

    assert db_session.query(User).count() == 0
    assert db_session.query(Role).count() == 0
    assert db_session.query(Permission).count() == 0
    assert (
        db_session.query(SystemConfig)
        .filter(SystemConfig.key == SETUP_KEY)
        .count()
        == 0
    )

    monkeypatch.setattr(auth_setup_integrity, "get_password_hash", original_hash)
    response = client.post(
        "/api/auth/setup",
        json=_request("retryadmin").model_dump(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert "user" not in payload  # Token response model intentionally filters extras.

    users = db_session.query(User).all()
    assert len(users) == 1
    assert users[0].username == "retryadmin"
    assert users[0].is_superuser is True
    assert db_session.query(Role).count() == len(auth_setup_integrity.SYSTEM_ROLE_CONFIG)
    assert db_session.query(Permission).count() == len(auth_setup_integrity.SYSTEM_PERMISSIONS)
    assert (
        db_session.query(SystemConfig)
        .filter(SystemConfig.key == SETUP_KEY)
        .count()
        == 1
    )


def test_concurrent_initial_setup_creates_exactly_one_super_admin(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Exercise a truly fresh installation: no users, roles, permissions or setup
    # marker exist before the two first-boot requests race each other.
    assert db_session.query(User).count() == 0
    assert db_session.query(Role).count() == 0
    assert db_session.query(Permission).count() == 0
    assert db_session.query(SystemConfig).filter(SystemConfig.key == SETUP_KEY).count() == 0

    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_session.get_bind(),
    )
    start = threading.Barrier(2)
    outcomes: list[tuple[str, int | str]] = []
    outcomes_lock = threading.Lock()

    def slow_hash(password: str) -> str:
        # Widen the old count-then-create race. With the canonical claim, the
        # second transaction is serialized before it can reach this point.
        time.sleep(0.2)
        return f"test-hash::{password}"

    monkeypatch.setattr(auth_setup_integrity, "get_password_hash", slow_hash)

    def worker(index: int) -> None:
        session = session_factory()
        try:
            start.wait(timeout=5)
            result = auth_setup_integrity.setup_initial_admin_integrity(
                _request(f"admin{index}"),
                session,
            )
            outcome: tuple[str, int | str] = (
                "success",
                result["user"].username,
            )
        except HTTPException as exc:
            outcome = ("http", exc.status_code)
        except Exception as exc:  # pragma: no cover - diagnostic safety
            outcome = ("error", type(exc).__name__)
        finally:
            session.close()

        with outcomes_lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=worker, args=(index,)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert len(outcomes) == 2
    assert sum(outcome[0] == "success" for outcome in outcomes) == 1
    assert sum(outcome == ("http", 403) for outcome in outcomes) == 1
    assert not [outcome for outcome in outcomes if outcome[0] == "error"]

    db_session.expire_all()
    users = db_session.query(User).all()
    assert len(users) == 1
    assert users[0].is_superuser is True
    assert users[0].role is not None
    assert users[0].role.name == "Super Admin"
    assert db_session.query(Role).count() == len(auth_setup_integrity.SYSTEM_ROLE_CONFIG)
    assert db_session.query(Permission).count() == len(auth_setup_integrity.SYSTEM_PERMISSIONS)

    claims = (
        db_session.query(SystemConfig)
        .filter(SystemConfig.key == SETUP_KEY)
        .all()
    )
    assert len(claims) == 1
    assert claims[0].value == users[0].username
