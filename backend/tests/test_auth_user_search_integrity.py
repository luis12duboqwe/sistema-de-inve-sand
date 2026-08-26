from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.routers import auth_admin_integrity, auth_router


def _user(username: str, full_name: str) -> User:
    return User(
        username=username,
        email=f"{username}@example.test",
        hashed_password="test-only",
        full_name=full_name,
        is_active=True,
        is_superuser=False,
    )


def _search_usernames(db_session: Session, search: str) -> set[str]:
    result = auth_admin_integrity.list_users_integrity(
        search=search,
        page=1,
        per_page=200,
        current_user=SimpleNamespace(),
        db=db_session,
    )
    return {item.username for item in result.items}


def _matching_get_routes(router) -> list:
    return [
        route
        for route in router.routes
        if getattr(route, "path", None) == "/api/auth/users"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]


def test_admin_user_search_treats_percent_as_literal(db_session: Session) -> None:
    suffix = uuid4().hex
    literal = _user(f"pctliteral{suffix}", f"Usuario pct%{suffix}")
    wildcard_decoy = _user(f"pctdecoy{suffix}", f"Usuario pctX{suffix}")
    db_session.add_all([literal, wildcard_decoy])
    db_session.commit()

    usernames = _search_usernames(db_session, f"pct%{suffix}")

    assert usernames == {literal.username}


def test_admin_user_search_treats_underscore_as_literal(db_session: Session) -> None:
    suffix = uuid4().hex
    literal = _user(f"underliteral{suffix}", f"Usuario under_{suffix}")
    wildcard_decoy = _user(f"underdecoy{suffix}", f"Usuario underX{suffix}")
    db_session.add_all([literal, wildcard_decoy])
    db_session.commit()

    usernames = _search_usernames(db_session, f"under_{suffix}")

    assert usernames == {literal.username}


def test_admin_user_search_treats_backslash_as_literal(db_session: Session) -> None:
    suffix = uuid4().hex
    literal = _user(f"slashliteral{suffix}", f"Usuario slash\\{suffix}")
    wildcard_decoy = _user(f"slashdecoy{suffix}", f"Usuario slashX{suffix}")
    db_session.add_all([literal, wildcard_decoy])
    db_session.commit()

    usernames = _search_usernames(db_session, f"slash\\{suffix}")

    assert usernames == {literal.username}


def test_admin_user_search_preserves_pagination_contract(db_session: Session) -> None:
    suffix = uuid4().hex
    db_session.add_all(
        [
            _user(f"pagea{suffix}", f"Grupo page-{suffix}"),
            _user(f"pageb{suffix}", f"Grupo page-{suffix}"),
        ]
    )
    db_session.commit()

    result = auth_admin_integrity.list_users_integrity(
        search=f"page-{suffix}",
        page=1,
        per_page=1,
        current_user=SimpleNamespace(),
        db=db_session,
    )

    assert result.total == 2
    assert result.page == 1
    assert result.per_page == 1
    assert result.pages == 2
    assert len(result.items) == 1


def test_admin_user_search_runtime_dispatch_is_canonical(
    client: TestClient,
    db_session: Session,
) -> None:
    legacy_matches = _matching_get_routes(auth_router.router)
    canonical_matches = _matching_get_routes(auth_admin_integrity.router)

    assert legacy_matches == []
    assert len(canonical_matches) == 1
    assert canonical_matches[0].endpoint is auth_admin_integrity.list_users_integrity

    suffix = uuid4().hex
    literal = _user(f"runtimeliteral{suffix}", f"Usuario runtime%{suffix}")
    wildcard_decoy = _user(f"runtimedecoy{suffix}", f"Usuario runtimeX{suffix}")
    db_session.add_all([literal, wildcard_decoy])
    db_session.commit()

    response = client.get(
        "/api/auth/users",
        params={"search": f"runtime%{suffix}", "per_page": 200},
    )

    assert response.status_code == 200, response.text
    assert {item["username"] for item in response.json()["items"]} == {literal.username}

    operation = client.get("/openapi.json").json()["paths"]["/api/auth/users"]["get"]
    assert operation["operationId"].startswith("list_users_integrity_")
