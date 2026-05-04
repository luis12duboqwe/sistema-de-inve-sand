import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from postgres_test_utils import create_postgres_test_engine


TEST_ENGINE, TEST_SCHEMA, cleanup_test_schema = create_postgres_test_engine("pytest")

import app.database as _db

_db.engine = TEST_ENGINE
_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

from app.main import app
import app.main as main
from app.database import Base, get_db
from app.auth import (
    check_permission,
    get_current_active_user,
    get_current_superuser,
    get_current_user,
    get_current_user_optional,
)

# Asegura que los modelos estén registrados en Base.metadata
from app import models as _models  # noqa: F401


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _enable_test_overrides():
    # DB de pruebas aislada en PostgreSQL
    app.dependency_overrides[get_db] = override_get_db

    # Health check estable
    main.check_db_connection = lambda: True

    # Autenticación: devolver siempre un usuario superusuario
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_current_user_optional] = _fake_user
    app.dependency_overrides[get_current_active_user] = _fake_user
    app.dependency_overrides[get_current_superuser] = _fake_user

    # Permisos: devolver usuario fake para cualquier permiso crítico usado en tests
    for perm_dep in [
        check_permission("inventory:create"),
        check_permission("inventory:edit"),
        check_permission("inventory:delete"),
        check_permission("inventory:view"),
        check_permission("orders:edit"),
        check_permission("orders:create"),
        check_permission("reports:view"),
    ]:
        app.dependency_overrides[perm_dep] = _fake_user


class _FakeUser:
    def __init__(self):
        self.id = 1
        self.username = "test"
        self.email = "test@example.com"
        self.is_active = True
        self.is_superuser = True
        self.role = None


def _fake_user():
    return _FakeUser()


@pytest.fixture(autouse=True)
def setup_database(request):
    """Config global de pruebas.

    - Tests unitarios/integración con TestClient: DB en memoria + auth fake + reset por test.
    - tests/test_api_usage.py: corre Uvicorn real y usa DB en archivo; NO aplicar overrides ni resets.
    """
    if "tests/test_api_usage.py" in request.node.nodeid:
        yield
        return

    previous_overrides = dict(app.dependency_overrides)
    previous_check_db_connection = getattr(main, "check_db_connection", None)

    _enable_test_overrides()
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=TEST_ENGINE)
        # Restaurar overrides previos (ej: los que define tests/test_api_usage.py)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

        if previous_check_db_connection is not None:
            main.check_db_connection = previous_check_db_connection


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    return TestClient(app)


def pytest_sessionfinish(session, exitstatus):
    cleanup_test_schema()
