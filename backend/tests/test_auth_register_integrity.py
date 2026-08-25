from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import User
from app.routers import auth_register_integrity
from app.schemas import UserCreate


PASSWORD = "StrongPass123!"


def _superuser():
    return SimpleNamespace(is_superuser=True)


def _run_concurrent_registration(db_session: Session, monkeypatch, payloads: list[UserCreate]):
    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = Barrier(2)

    def synchronized_hash(_: str) -> str:
        # Both requests have already passed username/email/role preflight when
        # they reach password hashing, so releasing them together deterministically
        # exercises the database uniqueness race rather than a sequential duplicate.
        barrier.wait(timeout=10)
        return "hashed"

    monkeypatch.setattr(auth_register_integrity, "get_password_hash", synchronized_hash)

    def register(payload: UserCreate):
        session = SessionLocal()
        try:
            try:
                created = auth_register_integrity.register_user_integrity(
                    payload,
                    session,
                    _superuser(),
                )
                return (201, created.username)
            except HTTPException as exc:
                return (exc.status_code, exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(register, payloads))


def test_register_duplicate_email_returns_client_error(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(
        User(
            username="existinguser",
            email="same@example.com",
            hashed_password="hashed",
            is_active=True,
            is_superuser=False,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": " same@example.com ",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Email already registered"


def test_concurrent_duplicate_username_is_never_reported_as_server_error(
    db_session: Session,
    monkeypatch,
) -> None:
    payloads = [
        UserCreate(
            username="raceuser",
            email="race-a@example.com",
            password=PASSWORD,
        ),
        UserCreate(
            username="raceuser",
            email="race-b@example.com",
            password=PASSWORD,
        ),
    ]

    results = _run_concurrent_registration(db_session, monkeypatch, payloads)

    assert sorted(status for status, _ in results) == [201, 400]
    assert any(
        detail == "Username already registered"
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert db_session.query(User).filter(User.username == "raceuser").count() == 1


def test_concurrent_duplicate_email_is_never_reported_as_server_error(
    db_session: Session,
    monkeypatch,
) -> None:
    payloads = [
        UserCreate(
            username="raceemaila",
            email="race@example.com",
            password=PASSWORD,
        ),
        UserCreate(
            username="raceemailb",
            email="race@example.com",
            password=PASSWORD,
        ),
    ]

    results = _run_concurrent_registration(db_session, monkeypatch, payloads)

    assert sorted(status for status, _ in results) == [201, 400]
    assert any(
        detail == "Email already registered"
        for status, detail in results
        if status == 400
    )

    db_session.expire_all()
    assert db_session.query(User).filter(User.email == "race@example.com").count() == 1


def test_unknown_integrity_conflict_is_not_mislabeled_as_duplicate(
    db_session: Session,
) -> None:
    error = auth_register_integrity._registration_integrity_error(
        db_session,
        "notpresent",
        "notpresent@example.com",
    )

    assert error.status_code == 409
    assert "retry" in str(error.detail).lower()


def test_register_route_is_canonical_in_openapi_and_runtime(
    client: TestClient,
    db_session: Session,
) -> None:
    schema_response = client.get("/openapi.json")
    assert schema_response.status_code == 200, schema_response.text
    register_path = schema_response.json()["paths"]["/api/auth/register"]
    assert set(register_path) == {"post"}
    assert register_path["post"]["operationId"].startswith("register_user_integrity_")

    response = client.post(
        "/api/auth/register",
        json={
            "username": "runtimeregisteruser",
            "email": "runtime-register@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["username"] == "runtimeregisteruser"

    db_session.expire_all()
    assert (
        db_session.query(User)
        .filter(User.username == "runtimeregisteruser")
        .count()
        == 1
    )
