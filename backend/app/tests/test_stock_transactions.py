from dataclasses import dataclass
from decimal import Decimal
from typing import List, TypedDict, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Location, Order, Product, ProductIMEI, Stock, TradeIn
from app.services.stock_transaction_helper import StockTransactionHelper
from app.utils.stock_manager import StockManager, StockValidationError


class InventorySetup(TypedDict):
    location: Location
    product: Product
    stock: Stock


class BaseSaleItemDict(TypedDict):
    product_id: int
    cantidad: int


class SaleItemDict(BaseSaleItemDict, total=False):
    precio_unitario: Decimal | None
    es_regalo_promocion: bool
    imeis: List[str] | None


@dataclass(slots=True)
class TradeInPayload:
    marca: str
    modelo: str
    condicion: str
    valor_estimado: Decimal
    color: str | None = None
    capacidad: str | None = None
    imei: str | None = None
    notas: str | None = None


def _ensure_pk(value: object, label: str) -> int:
    if not isinstance(value, int):
        raise AssertionError(f"{label} must be an int primary key")
    return value


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise AssertionError(f"{label} must be a string")
    return value


def _sale_item(
    *,
    product_id: int,
    cantidad: int,
    precio_unitario: Decimal | None = None,
    es_regalo_promocion: bool = False,
    imeis: List[str] | None = None,
) -> SaleItemDict:
    return {
        "product_id": product_id,
        "cantidad": cantidad,
        "precio_unitario": precio_unitario,
        "es_regalo_promocion": es_regalo_promocion,
        "imeis": imeis,
    }


@pytest.fixture()
def inventory_setup(db_session: Session) -> InventorySetup:
    location = Location(nombre="Test Store", tipo="tienda", direccion="", telefono="", activo=True)
    product = Product(
        sku="SKU-TEST-001",
        nombre="Telefono",
        categoria="telefonia",
        marca="Test",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("1000.00"),
        costo=Decimal("800.00"),
        moneda="HNL",
        garantia_meses=12,
        activo=True,
        is_serialized=False,
    )
    db_session.add(location)
    db_session.add(product)
    db_session.flush()

    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=10,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)
    db_session.commit()

    return {
        "location": location,
        "product": product,
        "stock": stock,
    }


def test_prepare_sale_items_blocks_stock(db_session: Session, inventory_setup: InventorySetup) -> None:
    helper = StockTransactionHelper(db_session)
    product = inventory_setup["product"]
    location = inventory_setup["location"]
    product_id = _ensure_pk(product.id, "product.id")
    location_id = _ensure_pk(location.id, "location.id")

    payload = _sale_item(product_id=product_id, cantidad=2)

    total, prepared_items = helper.prepare_sale_items(
        items_payload=[payload],
        location_id=location_id,
    )

    assert total == Decimal("2000.00")
    assert len(prepared_items) == 1
    locked_item = prepared_items[0]
    assert locked_item.product.id == product.id
    assert locked_item.cantidad == 2

    helper.stock_manager.decrease_stock(
        stock=locked_item.stock,
        quantity=locked_item.cantidad,
        operation_type="venta",
        notes="Test venta",
        user_id="pytest",
    )
    remaining_available = cast(int, locked_item.stock.cantidad_disponible)
    assert remaining_available == 8


def test_prepare_sale_items_rejects_insufficient_stock(db_session: Session, inventory_setup: InventorySetup) -> None:
    helper = StockTransactionHelper(db_session)
    product = inventory_setup["product"]
    location = inventory_setup["location"]
    product_id = _ensure_pk(product.id, "product.id")
    location_id = _ensure_pk(location.id, "location.id")

    payload = _sale_item(product_id=product_id, cantidad=50)

    with pytest.raises(HTTPException) as exc:
        helper.prepare_sale_items(items_payload=[payload], location_id=location_id)
    assert exc.value.status_code == 409


def test_serialized_items_require_imeis(db_session: Session) -> None:
    location = Location(nombre="Bodega", tipo="bodega", direccion="", telefono="", activo=True)
    product = Product(
        sku="SKU-IMEI-001",
        nombre="Smartphone",
        categoria="telefonia",
        marca="Marca",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("500.00"),
        costo=Decimal("300.00"),
        moneda="HNL",
        garantia_meses=12,
        activo=True,
        is_serialized=True,
    )
    db_session.add_all([location, product])
    db_session.flush()

    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=2,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)
    db_session.flush()

    imei_one = ProductIMEI(product_id=product.id, location_id=location.id, imei="111111111111111", vendido=False)
    imei_two = ProductIMEI(product_id=product.id, location_id=location.id, imei="222222222222222", vendido=False)
    db_session.add_all([imei_one, imei_two])
    db_session.commit()

    product_id = _ensure_pk(product.id, "product.id")
    location_id = _ensure_pk(location.id, "location.id")

    helper = StockTransactionHelper(db_session)
    payload_missing = _sale_item(product_id=product_id, cantidad=1)

    with pytest.raises(HTTPException) as exc:
        helper.prepare_sale_items(items_payload=[payload_missing], location_id=location_id)
    assert exc.value.status_code == 400

    payload_ok = _sale_item(
        product_id=product_id,
        cantidad=2,
        imeis=[
            _require_str(imei_one.imei, "imei_one.imei"),
            _require_str(imei_two.imei, "imei_two.imei"),
        ],
    )

    total, prepared_items = helper.prepare_sale_items(items_payload=[payload_ok], location_id=location_id)
    assert total == Decimal("1000.00")
    assert len(prepared_items[0].imeis_to_sell) == 2


def test_decrease_stock_prevents_reserved_underflow(db_session: Session, inventory_setup: InventorySetup) -> None:
    stock = inventory_setup["stock"]
    setattr(stock, "cantidad_reservada", 5)
    setattr(stock, "cantidad_disponible", 6)
    manager = StockManager(db_session)

    with pytest.raises(StockValidationError):
        manager.decrease_stock(
            stock=stock,
            quantity=2,
            operation_type="venta",
            notes="Force reserved underflow",
            user_id="pytest",
        )


def test_calculate_order_totals_handles_trade_ins(db_session: Session, inventory_setup: InventorySetup) -> None:
    helper = StockTransactionHelper(db_session)
    product = inventory_setup["product"]
    location = inventory_setup["location"]
    product_id = _ensure_pk(product.id, "product.id")
    location_id = _ensure_pk(location.id, "location.id")

    payload: List[SaleItemDict] = [
        _sale_item(
            product_id=product_id,
            cantidad=2,
        )
    ]

    sale_batch = helper.prepare_sale_batch(items_payload=payload, location_id=location_id)
    totals = helper.calculate_order_totals(sale_result=sale_batch, trade_in_total=Decimal("1500.00"))

    assert totals.subtotal == Decimal("2000.00")
    assert totals.trade_in_total == Decimal("1500.00")
    assert totals.total_after_trade_ins == Decimal("500.00")


def test_process_trade_ins_creates_records_and_stock(db_session: Session) -> None:
    location = Location(nombre="Bodega Retomas", tipo="bodega", direccion="", telefono="", activo=True)
    db_session.add(location)
    db_session.flush()

    order = Order(
        customer_name="Cliente Retoma",
        customer_phone="8888",
        canal="whatsapp",
        metodo_pago="efectivo",
        total=Decimal("0.00"),
        estado="pendiente",
        source_location_id=location.id,
    )
    db_session.add(order)
    db_session.flush()

    helper = StockTransactionHelper(db_session)
    trade_in_payload = [
        TradeInPayload(
            marca="Apple",
            modelo="iPhone 13",
            color="Rojo",
            capacidad="128GB",
            condicion="usado",
            valor_estimado=Decimal("5000.00"),
            imei="352099990000001",
            notas="Pantalla impecable",
        )
    ]

    total = helper.process_trade_ins(
        trade_ins_payload=trade_in_payload,
        db_order=order,
        profile_id_for_order=None,
        source_location_id=_ensure_pk(location.id, "location.id"),
        user_label="qa",
    )
    db_session.commit()

    assert total == Decimal("5000.00")
    order_pk = _ensure_pk(order.id, "order.id")
    assert db_session.query(TradeIn).filter_by(order_id=order_pk).count() == 1
    stock_entry = (
        db_session.query(Stock)
        .filter_by(location_id=_ensure_pk(location.id, "location.id"))
        .order_by(Stock.id.desc())
        .first()
    )
    assert stock_entry is not None
    available_stock = cast(int, stock_entry.cantidad_disponible)
    assert available_stock == 1
