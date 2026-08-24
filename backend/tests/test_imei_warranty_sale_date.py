from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import Order, Product, ProductIMEI, User
from app.routers.imeis import check_warranty_status


def _actor() -> User:
    return User(
        username="warranty-admin",
        email="warranty-admin@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_superuser=True,
    )


def _create_warranty_case(
    db_session,
    *,
    suffix: str,
    created_at: datetime,
    completed_at: datetime | None,
    sold_at: datetime | None,
):
    product = Product(
        sku=f"WARRANTY-{suffix}",
        nombre=f"Equipo {suffix}",
        categoria="celular",
        marca="Marca",
        modelo="Modelo",
        condicion="nuevo",
        precio=Decimal("10000.00"),
        costo=Decimal("7000.00"),
        moneda="Lps",
        garantia_meses=2,
        activo=True,
        is_serialized=True,
    )
    db_session.add(product)
    db_session.flush()

    order = Order(
        customer_name="Cliente Garantía",
        customer_phone="99999999",
        canal="tienda",
        metodo_pago="efectivo",
        total=Decimal("10000.00"),
        estado="completada",
        created_at=created_at,
        completed_at=completed_at,
    )
    db_session.add(order)
    db_session.flush()

    imei = ProductIMEI(
        product_id=product.id,
        location_id=None,
        imei=f"35678901234{suffix:0>4}"[-15:],
        vendido=True,
        order_id=order.id,
        sold_at=sold_at,
        acquisition_type="initial_stock",
    )
    db_session.add(imei)
    db_session.commit()
    return imei, order


def test_warranty_uses_imei_sold_at_before_order_dates(db_session):
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(days=90)
    completed_at = now - timedelta(days=30)
    sold_at = now - timedelta(days=5)
    imei, _ = _create_warranty_case(
        db_session,
        suffix="0001",
        created_at=created_at,
        completed_at=completed_at,
        sold_at=sold_at,
    )

    result = check_warranty_status(imei.imei, db=db_session, current_user=_actor())

    assert result["sale_date"] == sold_at
    assert result["expiration_date"] == sold_at + timedelta(days=60)
    assert result["status"] == "activa"


def test_warranty_falls_back_to_completed_at_for_legacy_imei(db_session):
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(days=90)
    completed_at = now - timedelta(days=10)
    imei, _ = _create_warranty_case(
        db_session,
        suffix="0002",
        created_at=created_at,
        completed_at=completed_at,
        sold_at=None,
    )

    result = check_warranty_status(imei.imei, db=db_session, current_user=_actor())

    assert result["sale_date"] == completed_at
    assert result["expiration_date"] == completed_at + timedelta(days=60)
    assert result["status"] == "activa"


def test_warranty_keeps_created_at_as_last_legacy_fallback(db_session):
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(days=10)
    imei, _ = _create_warranty_case(
        db_session,
        suffix="0003",
        created_at=created_at,
        completed_at=None,
        sold_at=None,
    )

    result = check_warranty_status(imei.imei, db=db_session, current_user=_actor())

    assert result["sale_date"] == created_at
    assert result["expiration_date"] == created_at + timedelta(days=60)
    assert result["status"] == "activa"
