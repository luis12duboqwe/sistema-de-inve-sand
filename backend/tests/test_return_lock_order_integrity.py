from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event

from app.models import Location, Order, Product, ProductIMEI, Stock
from app.routers import return_serial_integrity
from app.schemas import ReturnCreate


def _normalize(statement: str) -> str:
    return " ".join(statement.upper().split())


def test_return_prelock_uses_product_before_stock_protocol(db_session):
    suffix = uuid4().hex
    location = Location(nombre=f"Lock return {suffix}", tipo="tienda", activo=True)
    product = Product(
        sku=f"RET-LOCK-{suffix}",
        nombre=f"Equipo lock {suffix}",
        categoria="celular",
        marca="QA",
        modelo=f"L-{suffix[:8]}",
        condicion="nuevo",
        precio=Decimal("10000.00"),
        costo=Decimal("7000.00"),
        moneda="Lps",
        garantia_meses=12,
        activo=True,
        is_serialized=True,
    )
    db_session.add_all([location, product])
    db_session.flush()

    order = Order(
        source_location_id=location.id,
        customer_name="Cliente lock",
        customer_phone="77777777",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("10000.00"),
        estado="completada",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add_all(
        [
            Stock(
                product_id=product.id,
                location_id=location.id,
                cantidad_disponible=1,
                cantidad_reservada=0,
                cantidad_defectuosa=0,
            ),
            ProductIMEI(
                product_id=product.id,
                location_id=location.id,
                imei="357888888888888",
                vendido=False,
                acquisition_type="purchase_receipt",
            ),
        ]
    )
    db_session.commit()

    payload = ReturnCreate.model_validate(
        {
            "order_id": order.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "condition": "defectuoso",
                    "action": "warranty_exchange",
                    "imei": "357999999999995",
                    "replacement_imei": "357888888888888",
                }
            ],
        }
    )

    statements: list[str] = []
    bind = db_session.get_bind()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        normalized = _normalize(statement)
        if normalized.startswith("SELECT") and "FOR " in normalized:
            statements.append(normalized)

    event.listen(bind, "before_cursor_execute", before_cursor_execute)
    try:
        return_serial_integrity._prelock_return_stock_rows(db_session, payload)
    finally:
        event.remove(bind, "before_cursor_execute", before_cursor_execute)

    product_index = next(
        index
        for index, statement in enumerate(statements)
        if "FROM PRODUCTS" in statement and "FOR NO KEY UPDATE" in statement
    )
    stock_index = next(
        index
        for index, statement in enumerate(statements)
        if "FROM STOCK " in statement and "FOR UPDATE" in statement
    )

    assert product_index < stock_index
