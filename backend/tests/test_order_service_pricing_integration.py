from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Location, Order, Product, SalesProfile, Stock
from app.schemas import OrderCreate
from app.services.order_service import OrderService


def _seed_sale_context(db_session: Session, *, profile_type: str = "vendedor_humano"):
    location = Location(
        nombre=f"Tienda pricing {profile_type}",
        tipo="tienda",
        direccion="",
        telefono="",
        activo=True,
    )
    sales_profile = SalesProfile(
        name=f"Perfil pricing {profile_type}",
        slug=f"pricing-{profile_type}",
        tipo=profile_type,
        canales='["tienda"]',
        active=True,
    )
    product = Product(
        sku=f"PRICE-{profile_type}",
        nombre="Equipo pricing",
        categoria="celular",
        marca="Test",
        modelo="Pricing",
        condicion="nuevo",
        precio=Decimal("10000.00"),
        costo=Decimal("7000.00"),
        moneda="HNL",
        garantia_meses=12,
        activo=True,
        is_serialized=False,
    )
    db_session.add_all([location, sales_profile, product])
    db_session.flush()

    stock = Stock(
        product_id=product.id,
        location_id=location.id,
        cantidad_disponible=5,
        cantidad_reservada=0,
        cantidad_defectuosa=0,
    )
    db_session.add(stock)
    db_session.commit()

    return location, sales_profile, product, stock


def _order_payload(location: Location, sales_profile: SalesProfile, product: Product, price: str) -> OrderCreate:
    return OrderCreate.model_validate(
        {
            "sales_profile_slug": sales_profile.slug,
            "source_location_id": location.id,
            "canal": "tienda",
            "customer_name": "Cliente Pricing",
            "customer_phone": "99990000",
            "metodo_pago": "efectivo",
            "items": [
                {
                    "product_id": product.id,
                    "cantidad": 1,
                    "precio_unitario": price,
                }
            ],
        }
    )


def test_order_service_rejects_manipulated_deep_discount_and_rolls_back(db_session: Session):
    location, sales_profile, product, stock = _seed_sale_context(db_session)
    order = _order_payload(location, sales_profile, product, "9000.00")
    user = SimpleNamespace(username="vendedor-test", is_superuser=False)

    with pytest.raises(HTTPException) as exc:
        OrderService(db_session).create_order(order, current_user=user)

    assert exc.value.status_code == 403
    assert "supera el máximo permitido del 4%" in str(exc.value.detail)
    assert db_session.query(Order).count() == 0
    db_session.refresh(stock)
    assert stock.cantidad_disponible == 5


def test_order_service_allows_trusted_bot_three_percent_but_not_owner_tier(db_session: Session):
    location, sales_profile, product, stock = _seed_sale_context(db_session, profile_type="bot_ia")
    allowed_order = _order_payload(location, sales_profile, product, "9700.00")

    created = OrderService(db_session).create_order(allowed_order, current_user=None)

    assert created.total == Decimal("9700.00")
    assert created.items[0].precio_unitario == Decimal("9700.00")
    db_session.refresh(stock)
    assert stock.cantidad_disponible == 4

    owner_only_order = _order_payload(location, sales_profile, product, "9600.00")
    with pytest.raises(HTTPException) as exc:
        OrderService(db_session).create_order(owner_only_order, current_user=None)

    assert exc.value.status_code == 403
    assert "requiere aprobación del propietario" in str(exc.value.detail)
    db_session.refresh(stock)
    assert stock.cantidad_disponible == 4
