import threading

import pytest
from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Role, User
from app.routers.auth_router import ensure_default_rbac
from app.routers.super_admin import UserActiveRequest
from app.routers.super_admin_integrity import set_user_active_status_integrity


def _set_lock_timeouts(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SET LOCAL lock_timeout = '5s'"))
        session.execute(text("SET LOCAL statement_timeout = '10s'"))


def _seed_two_super_admins(db_session: Session) -> tuple[int, int]:
    ensure_default_rbac(db_session)
    role = db_session.query(Role).filter(Role.name == "Super Admin").one()
    first = User(
        username="concurrent-root-a",
        email="concurrent-root-a@example.com",
        full_name="Concurrent Root A",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
        role_id=role.id,
    )
    second = User(
        username="concurrent-root-b",
        email="concurrent-root-b@example.com",
        full_name="Concurrent Root B",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
        role_id=role.id,
    )
    db_session.add_all([first, second])
    db_session.commit()
    return first.id, second.id


def test_last_active_super_admin_cannot_be_deactivated_by_integrity_guard(db_session: Session) -> None:
    ensure_default_rbac(db_session)
    role = db_session.query(Role).filter(Role.name == "Super Admin").one()
    actor = User(
        username="only-root",
        email="only-root@example.com",
        full_name="Only Root",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
        role_id=role.id,
    )
    db_session.add(actor)
    db_session.commit()

    # The public endpoint already prevents self-deactivation. Exercise the shared
    # continuity invariant through a separate persisted actor so the test proves
    # that the final active administrator cannot be removed by state transition.
    shadow_actor = User(
        username="inactive-shadow-root",
        email="inactive-shadow-root@example.com",
        full_name="Inactive Shadow Root",
        hashed_password="test-hash",
        is_active=False,
        is_superuser=True,
        role_id=role.id,
    )
    db_session.add(shadow_actor)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        set_user_active_status_integrity(
            actor.id,
            UserActiveRequest(is_active=False, reason="Protección del último administrador"),
            db=db_session,
            current_user=shadow_actor,
        )

    # An inactive actor is never allowed to perform the mutation; importantly,
    # the target remains the final active Super Admin.
    assert exc_info.value.status_code == 403
    db_session.refresh(actor)
    assert actor.is_active is True
    assert actor.is_superuser is True


def test_concurrent_cross_deactivation_never_leaves_zero_active_super_admins(db_session: Session) -> None:
    if db_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Row-lock concurrency invariant requires PostgreSQL")

    first_id, second_id = _seed_two_super_admins(db_session)
    bind = db_session.get_bind()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    outcomes: list[int] = []

    def worker(actor_id: int, target_id: int) -> None:
        session: Session = SessionLocal()
        try:
            _set_lock_timeouts(session)
            actor = session.query(User).filter(User.id == actor_id).one()
            barrier.wait()
            set_user_active_status_integrity(
                target_id,
                UserActiveRequest(is_active=False, reason="Prueba de carrera Super Admin"),
                db=session,
                current_user=actor,
            )
            outcomes.append(200)
        except HTTPException as exc:
            session.rollback()
            outcomes.append(exc.status_code)
        except BaseException as exc:
            session.rollback()
            errors.append(exc)
        finally:
            session.close()

    threads = [
        threading.Thread(target=worker, args=(first_id, second_id), daemon=True),
        threading.Thread(target=worker, args=(second_id, first_id), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads), "Super Admin concurrency test deadlocked"
    assert errors == []
    assert len(outcomes) == 2
    assert outcomes.count(200) == 1
    assert any(status in {400, 403} for status in outcomes)

    db_session.expire_all()
    active_count = (
        db_session.query(func.count(User.id))
        .filter(User.is_superuser == True, User.is_active == True)
        .scalar()
        or 0
    )
    assert int(active_count) == 1
