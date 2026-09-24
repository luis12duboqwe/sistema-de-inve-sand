from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import (
    Location,
    Order,
    OrderItem,
    Product,
    ProductIMEI,
    Stock,
    StockHistory,
    StockTransfer,
    User,
    UserLocationAccess,
)
from app.routers import return_serial_integrity
from app.services.stock_transaction_helper import StockTransactionHelper
from app.utils.stock_manager import StockManager, StockValidationError


def _product(suffix: str) -> Product:
    return Product(
        sku=f"SERIAL-{suffix}",
        nombre=f"Equipo serial {suffix}",
        categoria="celular",
        marca="QA",
        modelo=f"M-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("10000.00"),
        costo=Decimal("7000.00"),
        moneda="Lps",
        garantia_meses=12,
        activo=True,
        is_serialized=True,
    )


def _location(name: str) -> Location:
    return Location(nombre=name, tipo="tienda", activo=True)


def _completed_order(db_session, location: Location, product: Product | None = None) -> Order:
    order = Order(
        source_location_id=location.id,
        customer_name="Cliente QA",
        customer_phone="99999999",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("10000.00"),
        estado="completada",
    )
    db_session.add(order)
    db_session.flush()
    if product is not None:
        db_session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                cantidad=1,
                precio_unitario=Decimal("10000.00"),
                costo_unitario=Decimal("7000.00"),
                es_regalo_promocion=False,
            )
        )
        db_session.flush()
    return order


def test_sale_cannot_consume_imei_reserved_for_pending_transfer(db_session):
    suffix = uuid4().hex
    product = _product(suffix)
    source = _location(f"Origen {suffix}")
    destination = _location(f"Destino {suffix}")
    db_session.add_all([product, source, destination])
    db_session.flush()

    stock = Stock(
        product_id=product.id,
        location_id=source.id,
        cantidad_disponible=2,
        cantidad_reservada=1,
        cantidad_defectuosa=0,
    )
    transfer = StockTransfer(
        product_id=product.id,
        from_location_id=source.id,
        to_location_id=destination.id,
        cantidad=1,
        estado="pendiente",
        created_by="qa",
    )
    db_session.add_all([stock, transfer])
    db_session.flush()

    reserved = ProductIMEI(
        product_id=product.id,
        location_id=source.id,
        imei="357111111111119",
        vendido=False,
        transfer_id=transfer.id,
        acquisition_type="purchase_receipt",
    )
    free = ProductIMEI(
        product_id=product.id,
        location_id=source.id,
        imei="357222222222226",
        vendido=False,
        acquisition_type="purchase_receipt",
    )
    db_session.add_all([reserved, free])
    db_session.commit()

    manager = StockManager(db_session)
    with pytest.raises(HTTPException) as exc:
        manager.validate_and_lock_stock(
            product_id=product.id,
            location_id=source.id,
            quantity=1,
            imeis_requested=[reserved.imei],
            allow_pending_imei=False,
            operation_type="sale",
        )
    assert exc.value.status_code == 409
    assert "transferencia pendiente" in str(exc.value.detail)

    _, _, selected = manager.validate_and_lock_stock(
        product_id=product.id,
        location_id=source.id,
        quantity=1,
        imeis_requested=[free.imei],
        allow_pending_imei=False,
        operation_type="sale",
    )
    assert [item.imei for item in selected] == [free.imei]


def test_defective_return_quarantines_imei_from_future_sale(db_session):
    suffix = uuid4().hex
    product = _product(suffix)
    location = _location(f"Garantías {suffix}")
    db_session.add_all([product, location])
    db_session.flush()
    order = _completed_order(db_session, location)
    db_session.add(
        Stock(
            product_id=product.id,
            location_id=location.id,
            cantidad_disponible=1,
            cantidad_reservada=0,
            cantidad_defectuosa=1,
        )
    )
    imei = ProductIMEI(
        product_id=product.id,
        location_id=location.id,
        imei="357333333333333",
        vendido=True,
        order_id=order.id,
        acquisition_type="purchase_receipt",
    )
    db_session.add(imei)
    db_session.flush()

    manager = StockManager(db_session)
    manager.process_return_imeis(
        [imei],
        return_id=101,
        condition="defectuoso",
        action="refund",
        user_id="qa",
    )
    db_session.flush()

    assert imei.vendido is False
    assert imei.order_id is None
    assert imei.acquisition_type == "devolucion_defectuosa"

    with pytest.raises(HTTPException) as exc:
        manager.validate_and_lock_stock(
            product_id=product.id,
            location_id=location.id,
            quantity=1,
            imeis_requested=[imei.imei],
            allow_pending_imei=False,
            operation_type="sale",
        )
    assert exc.value.status_code == 409
    assert "no está habilitado para venta" in str(exc.value.detail)


def test_warranty_replacement_requires_free_stock_and_records_negative_exit(db_session):
    suffix = uuid4().hex
    product = _product(suffix)
    location = _location(f"Reemplazos {suffix}")
    db_session.add_all([product, location])
    db_session.flush()
    order = _completed_order(db_session, location)

    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=1,
        cantidad_reservada=1,
        cantidad_defectuosa=0,
    )
    imei = ProductIMEI(
        product_id=product.id,
        location_id=location.id,
        imei="357444444444440",
        vendido=False,
        acquisition_type="purchase_receipt",
    )
    db_session.add_all([stock, imei])
    db_session.commit()

    manager = StockManager(db_session)
    with pytest.raises(StockValidationError):
        manager.process_warranty_replacement_imei(
            replacement_imei_record=imei,
            original_order_id=order.id,
            return_id=600,
            user_id="qa",
        )
    assert imei.vendido is False
    assert stock.cantidad_disponible == 1

    stock.cantidad_reservada = 0
    db_session.flush()
    manager.process_warranty_replacement_imei(
        replacement_imei_record=imei,
        original_order_id=order.id,
        return_id=601,
        user_id="qa",
    )
    db_session.flush()

    assert imei.vendido is True
    assert imei.order_id == order.id
    assert stock.cantidad_disponible == 0
    movement = (
        db_session.query(StockHistory)
        .filter(
            StockHistory.tipo_cambio == "garantia_salida",
            StockHistory.referencia_id == 601,
        )
        .one()
    )
    assert movement.cantidad == -1
    assert movement.stock_anterior == 1
    assert movement.stock_nuevo == 0


def test_warranty_replacement_cannot_use_imei_from_unauthorized_store(db_session):
    suffix = uuid4().hex
    product = _product(suffix)
    allowed = _location(f"Permitida {suffix}")
    denied = _location(f"Privada {suffix}")
    user = User(
        username=f"serial-{suffix[:8]}",
        email=f"serial-{suffix[:8]}@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=False,
    )
    db_session.add_all([product, allowed, denied, user])
    db_session.flush()
    order = _completed_order(db_session, allowed, product)
    db_session.add(
        UserLocationAccess(
            user_id=user.id,
            location_id=allowed.id,
            can_view=True,
            can_edit=True,
        )
    )
    db_session.add_all(
        [
            Stock(
                product_id=product.id,
                location_id=allowed.id,
                cantidad_disponible=0,
                cantidad_reservada=0,
                cantidad_defectuosa=1,
            ),
            Stock(
                product_id=product.id,
                location_id=denied.id,
                cantidad_disponible=1,
                cantidad_reservada=0,
                cantidad_defectuosa=0,
            ),
        ]
    )
    original = ProductIMEI(
        product_id=product.id,
        location_id=allowed.id,
        imei="357555555555557",
        vendido=True,
        order_id=order.id,
        acquisition_type="purchase_receipt",
    )
    replacement = ProductIMEI(
        product_id=product.id,
        location_id=denied.id,
        imei="357666666666664",
        vendido=False,
        acquisition_type="purchase_receipt",
    )
    db_session.add_all([original, replacement])
    db_session.commit()

    order_view = SimpleNamespace(
        id=order.id,
        estado="completada",
        items=[SimpleNamespace(product_id=product.id, cantidad=1, product=product)],
    )
    payload = [
        SimpleNamespace(
            product_id=product.id,
            quantity=1,
            condition="defectuoso",
            action="warranty_exchange",
            imei=original.imei,
            replacement_imei=replacement.imei,
        )
    ]

    token = return_serial_integrity._return_user.set(user)
    try:
        with pytest.raises(HTTPException) as exc:
            StockTransactionHelper(db_session).prepare_return_items(
                order=order_view,
                items_payload=payload,
            )
    finally:
        return_serial_integrity._return_user.reset(token)

    assert exc.value.status_code == 403
    assert f"ubicación {denied.id}" in str(exc.value.detail)
