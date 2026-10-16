"""Regression coverage for confirmed inventory defects in the October audit.

Run against the isolated PostgreSQL test database, never production data.
"""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import Location, Order, OrderItem, Product, ProductIMEI, Stock, StockHistory, StockTransfer, User
from app.routers.stock_transfer_integrity import confirm_transfer_integrity
from app.routers.orders import _finalize_order_stock, _release_pending_order_reservations
from app.schemas import StockTransferConfirm
from app.services.stock_transaction_helper import StockTransactionHelper


def _product(serialized=True):
    suffix = uuid4().hex
    return Product(
        sku=f"AUDIT-{suffix}", nombre=f"Equipo {suffix}",
        categoria="Telefonia", marca="QA", modelo="QA1",
        condicion="nuevo", precio=Decimal("3000.00"),
        costo=Decimal("1800.00"), activo=True, is_serialized=serialized,
    )


def _location():
    return Location(nombre=f"Tienda audit {uuid4().hex}", tipo="tienda", activo=True)


def _serial(product, location, *, order_id=None, transfer_id=None):
    return ProductIMEI(
        product_id=product.id, location_id=location.id,
        imei=f"3{uuid4().int % (10 ** 14):014d}",
        vendido=order_id is not None, order_id=order_id,
        transfer_id=transfer_id, acquisition_type="purchase_receipt",
    )


def _user():
    return User(
        username="audit-superuser", email="audit-superuser@example.com",
        hashed_password="test-hash", is_active=True, is_superuser=True,
    )


def _order(db_session, location, *products):
    order = Order(
        source_location_id=location.id, customer_name="Cliente QA",
        customer_phone="99999999", canal="tienda",
        metodo_pago="efectivo", total=Decimal("3000.00"),
        estado="completada",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add_all([
        OrderItem(
            order_id=order.id, product_id=product.id, cantidad=1,
            precio_unitario=Decimal("3000.00"), costo_unitario=Decimal("1800.00"),
            es_regalo_promocion=False,
        ) for product in products
    ])
    db_session.flush()
    return order


def _order_view(order, *products):
    return SimpleNamespace(
        id=order.id, estado="completada",
        items=[
            SimpleNamespace(product_id=p.id, cantidad=1, product=p)
            for p in products
        ],
    )


def test_zero_received_serialized_transfer_never_moves_imei(db_session):
    product, origin, destination = _product(), _location(), _location()
    db_session.add_all([product, origin, destination])
    db_session.flush()
    stock = Stock(
        product_id=product.id, location_id=origin.id,
        cantidad_disponible=5, cantidad_reservada=2, cantidad_defectuosa=0,
    )
    transfer = StockTransfer(
        product_id=product.id, from_location_id=origin.id,
        to_location_id=destination.id, cantidad=2,
        estado="pendiente", created_by="audit-superuser",
    )
    db_session.add_all([stock, transfer])
    db_session.flush()
    serials = [_serial(product, origin, transfer_id=transfer.id) for _ in range(2)]
    db_session.add_all(serials)
    db_session.commit()
    serial_ids = [x.id for x in serials]

    confirm_transfer_integrity(
        transfer.id,
        StockTransferConfirm(received_quantity=0, incident_notes="Ningún equipo recibido"),
        db=db_session,
        current_user=_user(),
    )
    db_session.expire_all()
    saved = db_session.query(ProductIMEI).filter(ProductIMEI.id.in_(serial_ids)).all()
    assert len(saved) == 2
    assert all(x.location_id == origin.id for x in saved)
    assert all(x.transfer_id is None for x in saved)
    refreshed_stock = db_session.get(Stock, stock.id)
    assert refreshed_stock.cantidad_disponible == 5
    assert refreshed_stock.cantidad_reservada == 0
    assert db_session.get(StockTransfer, transfer.id).received_quantity == 0


def test_cross_product_serial_cannot_be_returned_on_same_order(db_session):
    product_a, product_b, location = _product(), _product(), _location()
    db_session.add_all([product_a, product_b, location])
    db_session.flush()
    order = _order(db_session, location, product_a, product_b)
    original_a = _serial(product_a, location, order_id=order.id)
    replacement_b = _serial(product_b, location)
    db_session.add_all([original_a, replacement_b])
    db_session.commit()

    payload = [SimpleNamespace(
        product_id=product_b.id, quantity=1,
        condition="nuevo", action="warranty_exchange",
        imei=original_a.imei, replacement_imei=replacement_b.imei,
    )]
    with pytest.raises(HTTPException) as error:
        StockTransactionHelper(db_session).prepare_return_items(
            order=_order_view(order, product_a, product_b), items_payload=payload,
        )
    assert error.value.status_code == 400
    assert "no pertenece al producto" in str(error.value.detail)
    assert db_session.get(ProductIMEI, original_a.id).vendido is True


def test_serialized_warranty_rejects_missing_replacement_imei(db_session):
    product, location = _product(), _location()
    db_session.add_all([product, location])
    db_session.flush()
    order = _order(db_session, location, product)
    original = _serial(product, location, order_id=order.id)
    db_session.add(original)
    db_session.commit()

    payload = [SimpleNamespace(
        product_id=product.id, quantity=1,
        condition="nuevo", action="warranty_exchange",
        imei=original.imei, replacement_imei=None,
    )]
    with pytest.raises(HTTPException) as error:
        StockTransactionHelper(db_session).prepare_return_items(
            order=_order_view(order, product), items_payload=payload,
        )
    assert error.value.status_code == 400
    assert "requiere un IMEI de reemplazo" in str(error.value.detail)
    assert db_session.get(ProductIMEI, original.id).vendido is True


def test_trade_in_cannot_take_over_imei_sold_from_other_store(db_session):
    product_sold, trade_in_product = _product(), _product()
    original_location, intake_location = _location(), _location()
    db_session.add_all([product_sold, trade_in_product, original_location, intake_location])
    db_session.flush()
    order = _order(db_session, original_location, product_sold)
    sold_serial = _serial(product_sold, original_location, order_id=order.id)
    db_session.add(sold_serial)
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        StockTransactionHelper(db_session)._upsert_trade_in_imei(
            imei_value=sold_serial.imei, product_id=trade_in_product.id,
            location_id=intake_location.id, order_id=order.id,
            user_label="audit",
        )
    assert error.value.status_code == 409
    db_session.refresh(sold_serial)
    assert sold_serial.product_id == product_sold.id
    assert sold_serial.location_id == original_location.id
    assert sold_serial.vendido is True
    assert sold_serial.order_id == order.id


def test_trade_in_rejects_duplicate_imei_in_payload_before_writing(db_session):
    duplicated = "356123456789012"
    trade_ins = [
        SimpleNamespace(imei=duplicated, valor_estimado=Decimal("1000"), marca="QA", modelo="M1"),
        SimpleNamespace(imei=duplicated, valor_estimado=Decimal("1000"), marca="QA", modelo="M1"),
    ]
    with pytest.raises(HTTPException) as error:
        StockTransactionHelper(db_session).process_trade_ins(
            trade_ins_payload=trade_ins, db_order=None,
            profile_id_for_order=None, source_location_id=1, user_label="audit",
        )
    assert error.value.status_code == 400
    assert "duplicados" in str(error.value.detail)


def _sale_with_other_transfer_reservation(db_session):
    product, location = _product(serialized=False), _location()
    db_session.add_all([product, location])
    db_session.flush()
    order = Order(
        source_location_id=location.id, customer_name="Cliente reserva",
        customer_phone="99999999", canal="tienda",
        metodo_pago="efectivo", total=Decimal("3000.00"), estado="pendiente",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add_all([
        OrderItem(
            order_id=order.id, product_id=product.id, cantidad=1,
            precio_unitario=Decimal("3000"), costo_unitario=Decimal("1800"),
            es_regalo_promocion=False,
        ),
        Stock(
            product_id=product.id, location_id=location.id,
            cantidad_disponible=9, cantidad_reservada=3, cantidad_defectuosa=0,
        ),
        StockHistory(
            product_id=product.id, location_id=location.id,
            tipo_cambio="venta", cantidad=-1,
            stock_anterior=10, stock_nuevo=9,
            referencia_id=order.id, referencia_tipo="order",
            usuario="audit",
        ),
    ])
    db_session.commit()
    db_session.refresh(order)
    return product, location, order


def test_completing_debited_sale_does_not_consume_other_transfer_reservation(db_session):
    product, location, order = _sale_with_other_transfer_reservation(db_session)
    _finalize_order_stock(db_session, order, "audit")
    db_session.flush()
    stock = db_session.query(Stock).filter_by(
        product_id=product.id, location_id=location.id,
    ).one()
    assert stock.cantidad_disponible == 9
    assert stock.cantidad_reservada == 3


def test_canceling_debited_pending_sale_restores_stock_not_other_reservation(db_session):
    product, location, order = _sale_with_other_transfer_reservation(db_session)
    _release_pending_order_reservations(
        db_session, order, "audit", "Venta cancelada",
    )
    db_session.flush()
    stock = db_session.query(Stock).filter_by(
        product_id=product.id, location_id=location.id,
    ).one()
    assert stock.cantidad_disponible == 10
    assert stock.cantidad_reservada == 3
