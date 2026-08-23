import pytest
from fastapi import HTTPException

from app.models import Location, Product, Stock, StockHistory, User, UserLocationAccess
from app.routers.stock_history import (
    create_stock_history_entry,
    get_location_stock_history,
    get_product_stock_history,
    get_product_stock_stats,
)
from app.schemas import StockHistoryCreate


def _product() -> Product:
    return Product(
        sku="HISTORY-TEST-001",
        nombre="Producto Historial",
        categoria="Telefonía",
        marca="Test",
        modelo="H1",
        condicion="nuevo",
        precio=100,
        costo=50,
        activo=True,
        is_serialized=False,
    )


def _user(username: str, *, superuser: bool = False) -> User:
    return User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=superuser,
    )


def _seed_scoped_history(db_session):
    product = _product()
    allowed = Location(nombre="Tienda historial permitida", tipo="tienda", activo=True)
    denied = Location(nombre="Tienda historial privada", tipo="tienda", activo=True)
    viewer = _user("history-viewer")
    editor = _user("history-editor")
    db_session.add_all([product, allowed, denied, viewer, editor])
    db_session.flush()

    db_session.add_all(
        [
            UserLocationAccess(user_id=viewer.id, location_id=allowed.id, can_view=True, can_edit=False),
            UserLocationAccess(user_id=editor.id, location_id=allowed.id, can_view=True, can_edit=True),
            Stock(
                product_id=product.id,
                location_id=allowed.id,
                cantidad_disponible=10,
                cantidad_reservada=2,
                cantidad_defectuosa=0,
            ),
            Stock(
                product_id=product.id,
                location_id=denied.id,
                cantidad_disponible=20,
                cantidad_reservada=0,
                cantidad_defectuosa=0,
            ),
            StockHistory(
                product_id=product.id,
                location_id=allowed.id,
                tipo_cambio="compra",
                cantidad=5,
                stock_anterior=5,
                stock_nuevo=10,
                usuario="system",
            ),
            StockHistory(
                product_id=product.id,
                location_id=allowed.id,
                tipo_cambio="venta",
                cantidad=-2,
                stock_anterior=10,
                stock_nuevo=8,
                usuario="system",
            ),
            StockHistory(
                product_id=product.id,
                location_id=denied.id,
                tipo_cambio="compra",
                cantidad=100,
                stock_anterior=0,
                stock_nuevo=100,
                usuario="system",
            ),
        ]
    )
    db_session.commit()
    return product, allowed, denied, viewer, editor


def test_stock_history_returns_404_for_missing_product_and_location(db_session):
    actor = _user("root-history", superuser=True)

    with pytest.raises(HTTPException) as product_exc:
        get_product_stock_history(
            999999,
            limit=100,
            location_id=None,
            tipo_cambio=None,
            date_from=None,
            date_to=None,
            db=db_session,
            current_user=actor,
        )
    assert product_exc.value.status_code == 404

    with pytest.raises(HTTPException) as location_exc:
        get_location_stock_history(
            999999,
            limit=100,
            tipo_cambio=None,
            days=30,
            db=db_session,
            current_user=actor,
        )
    assert location_exc.value.status_code == 404


def test_product_history_is_scoped_to_authorized_locations(db_session):
    product, allowed, denied, viewer, _ = _seed_scoped_history(db_session)

    history = get_product_stock_history(
        product.id,
        limit=100,
        location_id=None,
        tipo_cambio=None,
        date_from=None,
        date_to=None,
        db=db_session,
        current_user=viewer,
    )

    assert len(history) == 2
    assert {row.location_id for row in history} == {allowed.id}
    assert all(row.location_id != denied.id for row in history)


def test_explicit_location_history_denies_unauthorized_location(db_session):
    _, _, denied, viewer, _ = _seed_scoped_history(db_session)

    with pytest.raises(HTTPException) as exc_info:
        get_location_stock_history(
            denied.id,
            limit=100,
            tipo_cambio=None,
            days=30,
            db=db_session,
            current_user=viewer,
        )

    assert exc_info.value.status_code == 403


def test_stock_stats_exclude_inaccessible_locations_and_reserved_units(db_session):
    product, allowed, _, viewer, _ = _seed_scoped_history(db_session)

    stats = get_product_stock_stats(
        product.id,
        days=30,
        db=db_session,
        current_user=viewer,
    )

    assert stats["total_movements"] == 2
    assert stats["movements_by_type"] == {"compra": 1, "venta": 1}
    assert stats["total_entrada"] == 5
    assert stats["total_salida"] == 2
    assert stats["stock_actual"] == 8
    assert stats["product_id"] == product.id
    assert allowed.id is not None


def test_manual_history_entry_is_append_only_and_does_not_mutate_stock(db_session):
    product, allowed, _, _, editor = _seed_scoped_history(db_session)
    stock = db_session.query(Stock).filter(
        Stock.product_id == product.id,
        Stock.location_id == allowed.id,
    ).one()
    before = (stock.cantidad_disponible, stock.cantidad_reservada, stock.cantidad_defectuosa)

    entry = create_stock_history_entry(
        StockHistoryCreate(
            product_id=product.id,
            location_id=allowed.id,
            tipo_cambio="nota_auditoria",
            cantidad=0,
            stock_anterior=stock.cantidad_disponible,
            stock_nuevo=stock.cantidad_disponible,
            notas="Registro manual de auditoría sin mutar stock",
            usuario=editor.username,
        ),
        db=db_session,
        current_user=editor,
    )

    db_session.refresh(stock)
    after = (stock.cantidad_disponible, stock.cantidad_reservada, stock.cantidad_defectuosa)
    assert entry.id is not None
    assert entry.location_id == allowed.id
    assert before == after


def test_manual_history_entry_requires_edit_access_to_location(db_session):
    product, allowed, _, viewer, _ = _seed_scoped_history(db_session)

    with pytest.raises(HTTPException) as exc_info:
        create_stock_history_entry(
            StockHistoryCreate(
                product_id=product.id,
                location_id=allowed.id,
                tipo_cambio="nota_auditoria",
                cantidad=0,
                stock_anterior=10,
                stock_nuevo=10,
                usuario=viewer.username,
            ),
            db=db_session,
            current_user=viewer,
        )

    assert exc_info.value.status_code == 403
