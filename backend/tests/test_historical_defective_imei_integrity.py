from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import Location, Order, Product, ProductIMEI, Return, ReturnItem, Stock
from app.routers import return_serial_integrity  # noqa: F401 - installs shared serial guards
from app.utils.stock_manager import StockManager


def test_historical_defective_return_remains_unsellable_without_new_marker(db_session):
    suffix = uuid4().hex
    location = Location(nombre=f"Histórica {suffix}", tipo="tienda", activo=True)
    product = Product(
        sku=f"HIST-{suffix}",
        nombre=f"Equipo histórico {suffix}",
        categoria="celular",
        marca="QA",
        modelo=f"H-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("9000.00"),
        costo=Decimal("6000.00"),
        moneda="Lps",
        garantia_meses=12,
        activo=True,
        is_serialized=True,
    )
    db_session.add_all([location, product])
    db_session.flush()

    order = Order(
        source_location_id=location.id,
        customer_name="Cliente histórico",
        customer_phone="88888888",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("9000.00"),
        estado="completada",
    )
    db_session.add(order)
    db_session.flush()

    returned = Return(
        order_id=order.id,
        reason="Defectuoso histórico",
        status="completed",
        created_by="legacy",
    )
    db_session.add(returned)
    db_session.flush()

    imei_value = "357777777777771"
    db_session.add_all(
        [
            ReturnItem(
                return_id=returned.id,
                product_id=product.id,
                quantity=1,
                condition="defectuoso",
                action="refund",
                imei=imei_value,
            ),
            Stock(
                product_id=product.id,
                location_id=location.id,
                cantidad_disponible=1,
                cantidad_reservada=0,
                cantidad_defectuosa=1,
            ),
            ProductIMEI(
                product_id=product.id,
                location_id=location.id,
                imei=imei_value,
                vendido=False,
                acquisition_type="purchase_receipt",
            ),
        ]
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        StockManager(db_session).validate_and_lock_stock(
            product_id=product.id,
            location_id=location.id,
            quantity=1,
            imeis_requested=[imei_value],
            allow_pending_imei=False,
            operation_type="sale",
        )

    assert exc.value.status_code == 409
    assert "no está habilitado para venta" in str(exc.value.detail)
