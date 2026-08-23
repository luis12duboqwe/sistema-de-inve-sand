import pytest
from fastapi import HTTPException

from app.models import Permission, Role, User
from app.routers.auth_router import (
    SYSTEM_PERMISSIONS,
    SYSTEM_ROLE_CONFIG,
    _is_super_admin_role,
    _require_superuser_for_super_admin_role,
    _require_superuser_for_super_admin_target,
    ensure_default_rbac,
    ensure_superuser_has_role,
)


def _user(username: str, *, is_superuser: bool = False, role_id: int | None = None) -> User:
    return User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=is_superuser,
        role_id=role_id,
    )


def test_ensure_default_rbac_creates_complete_system_catalog_and_is_idempotent(db_session):
    ensure_default_rbac(db_session)

    permissions = db_session.query(Permission).all()
    roles = db_session.query(Role).all()

    assert {item.slug for item in permissions} == {item["slug"] for item in SYSTEM_PERMISSIONS}
    assert {role.name for role in roles} == {item["name"] for item in SYSTEM_ROLE_CONFIG}
    assert all(role.is_system_role for role in roles)

    for definition in SYSTEM_ROLE_CONFIG:
        role = next(item for item in roles if item.name == definition["name"])
        assert {permission.slug for permission in role.permissions} == set(definition["permission_slugs"])

    permission_count = len(permissions)
    role_count = len(roles)
    ensure_default_rbac(db_session)

    assert db_session.query(Permission).count() == permission_count
    assert db_session.query(Role).count() == role_count


def test_ensure_default_rbac_repairs_missing_required_permission_and_system_flag(db_session):
    ensure_default_rbac(db_session)

    admin = db_session.query(Role).filter(Role.name == "Admin").one()
    required = next(item for item in SYSTEM_ROLE_CONFIG if item["name"] == "Admin")
    removed_slug = required["permission_slugs"][0]
    admin.permissions = [permission for permission in admin.permissions if permission.slug != removed_slug]
    admin.is_system_role = False
    db_session.commit()

    ensure_default_rbac(db_session)
    db_session.refresh(admin)

    assert admin.is_system_role is True
    assert set(required["permission_slugs"]).issubset({permission.slug for permission in admin.permissions})


def test_ensure_superuser_has_super_admin_role_without_promoting_regular_users(db_session):
    ensure_default_rbac(db_session)
    super_admin_role = db_session.query(Role).filter(Role.name == "Super Admin").one()
    seller_role = db_session.query(Role).filter(Role.name == "Vendedor").one()

    superuser = _user("root-user", is_superuser=True, role_id=seller_role.id)
    regular_user = _user("regular-user", is_superuser=False, role_id=seller_role.id)
    db_session.add_all([superuser, regular_user])
    db_session.commit()

    ensure_superuser_has_role(db_session, superuser)
    ensure_superuser_has_role(db_session, regular_user)

    assert superuser.role_id == super_admin_role.id
    assert regular_user.role_id == seller_role.id


def test_super_admin_role_detection_is_normalized():
    assert _is_super_admin_role(Role(name="Super Admin")) is True
    assert _is_super_admin_role(Role(name=" superadmin ")) is True
    assert _is_super_admin_role(Role(name="Admin")) is False
    assert _is_super_admin_role(None) is False


def test_non_superuser_cannot_assign_super_admin_role():
    actor = _user("actor", is_superuser=False)
    super_admin_role = Role(name="Super Admin")

    with pytest.raises(HTTPException) as exc_info:
        _require_superuser_for_super_admin_role(actor, super_admin_role)

    assert exc_info.value.status_code == 403

    actor.is_superuser = True
    _require_superuser_for_super_admin_role(actor, super_admin_role)


def test_non_superuser_cannot_modify_superuser_target():
    actor = _user("actor", is_superuser=False)
    target = _user("target", is_superuser=True)

    with pytest.raises(HTTPException) as exc_info:
        _require_superuser_for_super_admin_target(actor, target)

    assert exc_info.value.status_code == 403

    actor.is_superuser = True
    _require_superuser_for_super_admin_target(actor, target)
