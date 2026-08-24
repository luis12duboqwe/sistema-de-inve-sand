import pytest
from fastapi import HTTPException

from app.models import Location, Order, SalesProfile, User, UserLocationAccess
from app.routers.sales_profiles import (
    create_sales_profile,
    delete_sales_profile,
    get_sales_profile,
    get_sales_profile_by_slug,
    get_sales_profile_orders,
    update_sales_profile,
)
from app.schemas import SalesProfileCreate, SalesProfileUpdate


def _actor(username: str = "profile-admin", *, superuser: bool = True) -> User:
    return User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=superuser,
    )


def _profile(name: str, slug: str, *, tipo: str = "bot_ia") -> SalesProfile:
    return SalesProfile(name=name, slug=slug, tipo=tipo, active=True)


def test_sales_profile_lookup_returns_404_for_missing_id_and_slug(db_session):
    with pytest.raises(HTTPException) as id_exc:
        get_sales_profile(999999, db=db_session)
    assert id_exc.value.status_code == 404

    with pytest.raises(HTTPException) as slug_exc:
        get_sales_profile_by_slug("missing-profile", db=db_session)
    assert slug_exc.value.status_code == 404


def test_create_sales_profile_rejects_case_insensitive_duplicate_slug(db_session):
    db_session.add(_profile("Bot existente", "softmobile-bot"))
    db_session.commit()

    payload = SalesProfileCreate(
        name="Bot duplicado",
        slug="SOFTMOBILE-BOT",
        tipo="bot_ia",
        canales=["whatsapp"],
    )

    with pytest.raises(HTTPException) as exc_info:
        create_sales_profile(payload, db=db_session, current_user=_actor())

    assert exc_info.value.status_code == 400
    assert "ignora mayúsculas/minúsculas" in exc_info.value.detail
    assert db_session.query(SalesProfile).count() == 1


def test_update_sales_profile_rejects_case_insensitive_duplicate_slug(db_session):
    first = _profile("Bot uno", "bot-uno")
    second = _profile("Bot dos", "bot-dos")
    db_session.add_all([first, second])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_sales_profile(
            second.id,
            SalesProfileUpdate(slug="BOT-UNO"),
            db=db_session,
            current_user=_actor(),
        )

    assert exc_info.value.status_code == 400
    db_session.refresh(second)
    assert second.slug == "bot-dos"


def test_delete_sales_profile_preserves_profiles_with_historical_orders(db_session):
    profile = _profile("Perfil con ventas", "perfil-con-ventas")
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        Order(
            sales_profile_id=profile.id,
            customer_name="Cliente histórico",
            customer_phone="99990000",
            canal="whatsapp",
            metodo_pago="efectivo",
            total=100,
            estado="completada",
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_sales_profile(profile.id, db=db_session, current_user=_actor())

    assert exc_info.value.status_code == 400
    assert "órdenes históricas asociadas" in exc_info.value.detail
    assert db_session.query(SalesProfile).filter(SalesProfile.id == profile.id).one_or_none() is not None


def test_delete_unused_sales_profile_removes_it(db_session):
    profile = _profile("Perfil sin ventas", "perfil-sin-ventas")
    db_session.add(profile)
    db_session.commit()
    profile_id = profile.id

    assert delete_sales_profile(profile_id, db=db_session, current_user=_actor()) is None
    assert db_session.query(SalesProfile).filter(SalesProfile.id == profile_id).one_or_none() is None


def test_sales_profile_orders_are_scoped_to_authorized_locations(db_session):
    profile = _profile("Bot multi tienda", "bot-multi-tienda")
    location_allowed = Location(nombre="Tienda permitida", tipo="tienda", activo=True)
    location_denied = Location(nombre="Tienda no permitida", tipo="tienda", activo=True)
    user = _actor("scoped-user", superuser=False)
    db_session.add_all([profile, location_allowed, location_denied, user])
    db_session.flush()

    db_session.add(
        UserLocationAccess(
            user_id=user.id,
            location_id=location_allowed.id,
            can_view=True,
            can_edit=False,
        )
    )
    db_session.add_all(
        [
            Order(
                sales_profile_id=profile.id,
                source_location_id=location_allowed.id,
                customer_name="Cliente permitido",
                customer_phone="99990001",
                canal="whatsapp",
                metodo_pago="efectivo",
                total=100,
                estado="completada",
            ),
            Order(
                sales_profile_id=profile.id,
                source_location_id=location_denied.id,
                customer_name="Cliente oculto",
                customer_phone="99990002",
                canal="facebook",
                metodo_pago="efectivo",
                total=200,
                estado="completada",
            ),
        ]
    )
    db_session.commit()

    orders = get_sales_profile_orders(
        profile.id,
        skip=0,
        limit=100,
        db=db_session,
        current_user=user,
    )

    assert [order.customer_name for order in orders] == ["Cliente permitido"]
    assert all(order.source_location_id == location_allowed.id for order in orders)
