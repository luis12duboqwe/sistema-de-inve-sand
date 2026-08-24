import pytest
from fastapi import HTTPException

from app.models import Role, User
from app.routers.auth_router import (
    ensure_default_rbac,
    register_user,
    update_user_admin,
    update_user_me,
    update_user_role,
)
from app.schemas import UserCreate, UserUpdate


def _user(username: str, *, is_superuser: bool = False, role_id: int | None = None) -> User:
    return User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        hashed_password="test-hash",
        is_active=True,
        is_superuser=is_superuser,
        role_id=role_id,
    )


def _roles(db_session) -> tuple[Role, Role]:
    ensure_default_rbac(db_session)
    super_admin = db_session.query(Role).filter(Role.name == "Super Admin").one()
    seller = db_session.query(Role).filter(Role.name == "Vendedor").one()
    return super_admin, seller


def test_self_update_cannot_change_username_role_or_active_flag(db_session):
    super_admin_role, seller_role = _roles(db_session)
    user = _user("self-editor", role_id=seller_role.id)
    db_session.add(user)
    db_session.commit()

    response = update_user_me(
        UserUpdate(
            username="escalateduser",
            role_id=super_admin_role.id,
            is_active=False,
            full_name="Nombre permitido",
        ),
        current_user=user,
        db=db_session,
    )

    assert response.username == "self-editor"
    assert response.role_id == seller_role.id
    assert response.is_superuser is False
    assert response.is_active is True
    assert response.full_name == "Nombre permitido"


def test_superuser_role_assignment_keeps_superuser_flag_in_sync(db_session):
    super_admin_role, seller_role = _roles(db_session)
    actor = _user("root-role-admin", is_superuser=True, role_id=super_admin_role.id)
    target = _user("role-target", role_id=seller_role.id)
    db_session.add_all([actor, target])
    db_session.commit()

    promoted = update_user_role(
        target.id,
        role_id=super_admin_role.id,
        current_user=actor,
        db=db_session,
    )
    assert promoted.role_id == super_admin_role.id
    assert promoted.is_superuser is True

    demoted = update_user_role(
        target.id,
        role_id=seller_role.id,
        current_user=actor,
        db=db_session,
    )
    assert demoted.role_id == seller_role.id
    assert demoted.is_superuser is False


def test_non_superuser_cannot_promote_user_to_super_admin(db_session):
    super_admin_role, seller_role = _roles(db_session)
    actor = _user("manager-actor", role_id=seller_role.id)
    target = _user("manager-target", role_id=seller_role.id)
    db_session.add_all([actor, target])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_user_role(
            target.id,
            role_id=super_admin_role.id,
            current_user=actor,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    db_session.refresh(target)
    assert target.role_id == seller_role.id
    assert target.is_superuser is False


def test_non_superuser_cannot_modify_existing_superuser(db_session):
    super_admin_role, seller_role = _roles(db_session)
    actor = _user("limited-admin", role_id=seller_role.id)
    target = _user("protected-root", is_superuser=True, role_id=super_admin_role.id)
    db_session.add_all([actor, target])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_user_admin(
            target.id,
            UserUpdate(full_name="No debe cambiar"),
            current_user=actor,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    db_session.refresh(target)
    assert target.full_name == "protected-root"
    assert target.is_superuser is True


def test_register_user_rejects_super_admin_role_for_non_superuser(db_session):
    super_admin_role, seller_role = _roles(db_session)
    actor = _user("registration-manager", role_id=seller_role.id)
    db_session.add(actor)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        register_user(
            UserCreate(
                username="newroot",
                email="newroot@example.com",
                full_name="Nuevo Root",
                password="StrongPassword1!",
                role_id=super_admin_role.id,
            ),
            db=db_session,
            current_user=actor,
        )

    assert exc_info.value.status_code == 403
    assert db_session.query(User).filter(User.username == "newroot").first() is None


def test_register_user_rejects_unknown_role_without_creating_user(db_session):
    _, seller_role = _roles(db_session)
    actor = _user("root-registration", is_superuser=True, role_id=seller_role.id)
    db_session.add(actor)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        register_user(
            UserCreate(
                username="badroleuser",
                email="badroleuser@example.com",
                full_name="Rol inexistente",
                password="StrongPassword1!",
                role_id=999999,
            ),
            db=db_session,
            current_user=actor,
        )

    assert exc_info.value.status_code == 404
    assert db_session.query(User).filter(User.username == "badroleuser").first() is None
