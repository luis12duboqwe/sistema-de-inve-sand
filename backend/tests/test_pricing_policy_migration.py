from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.models import AIProfileConfig, SalesProfile
from app.schemas import AIConfigSchema
from app.utils.ai_sales_policy import (
    CANONICAL_DISCOUNT_CONTEXT_RULE,
    POLICY_MARKER,
    ensure_canonical_discount_context_rules,
)
from app.utils.order_pricing import enforce_sale_price_policy
from app.utils.pricing_policy_migration import (
    MIGRATION_ID,
    ORDER_CURRENCY_MIGRATION_ID,
    run_pricing_policy_migration,
)


def test_ai_config_schema_caps_new_configuration_at_three_percent():
    valid = AIConfigSchema(
        sales_profile_id=1,
        system_prompt="Vende sin exceder las reglas.",
        context_rules="Regla personalizada del negocio.",
        max_discount_rate=0.03,
    )
    assert valid.max_discount_rate == 0.03
    assert valid.context_rules is not None
    assert "Regla personalizada del negocio." in valid.context_rules
    assert valid.context_rules.count(POLICY_MARKER) == 1

    with pytest.raises(ValidationError):
        AIConfigSchema(
            sales_profile_id=1,
            system_prompt="No válido",
            max_discount_rate=0.031,
        )


def test_canonical_policy_preserves_custom_rules_before_and_after_existing_block():
    raw = (
        "Regla personalizada antes.\n\n"
        f"{CANONICAL_DISCOUNT_CONTEXT_RULE}\n\n"
        "Regla personalizada después."
    )

    normalized = ensure_canonical_discount_context_rules(raw)

    assert "Regla personalizada antes." in normalized
    assert "Regla personalizada después." in normalized
    assert normalized.count(POLICY_MARKER) == 1
    assert normalized.endswith(CANONICAL_DISCOUNT_CONTEXT_RULE)


def test_pricing_policy_migration_clamps_historical_ai_discount_once(db_session: Session):
    sales_profile = SalesProfile(
        name="Bot histórico pricing",
        slug="bot-historico-pricing",
        tipo="bot_ia",
        canales='["whatsapp"]',
        active=True,
    )
    db_session.add(sales_profile)
    db_session.flush()

    historical = AIProfileConfig(
        sales_profile_id=sales_profile.id,
        system_prompt="Prompt histórico que incluso pudo contener reglas viejas.",
        context_rules=(
            "Conserva esta regla personalizada antes.\n\n"
            f"{CANONICAL_DISCOUNT_CONTEXT_RULE}\n\n"
            "Conserva también esta regla personalizada después."
        ),
        max_discount_rate=Decimal("0.1500"),
    )
    db_session.add(historical)
    db_session.commit()

    historical_id = historical.id
    test_engine = db_session.get_bind()
    assert run_pricing_policy_migration(bind=test_engine) is True

    verification_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    with verification_session_factory() as verification_session:
        migrated = verification_session.query(AIProfileConfig).filter_by(id=historical_id).one()
        assert Decimal(str(migrated.max_discount_rate)) == Decimal("0.0300")
        assert migrated.context_rules is not None
        assert "Conserva esta regla personalizada antes." in migrated.context_rules
        assert "Conserva también esta regla personalizada después." in migrated.context_rules
        assert migrated.context_rules.count(POLICY_MARKER) == 1
        rules_after_first_run = migrated.context_rules

        ledger_count = verification_session.execute(
            text("SELECT COUNT(*) FROM schema_migrations WHERE id = :migration_id"),
            {"migration_id": MIGRATION_ID},
        ).scalar_one()
        assert int(ledger_count) == 1

    assert run_pricing_policy_migration(bind=test_engine) is True
    with verification_session_factory() as verification_session:
        migrated_again = verification_session.query(AIProfileConfig).filter_by(id=historical_id).one()
        assert Decimal(str(migrated_again.max_discount_rate)) == Decimal("0.0300")
        assert migrated_again.context_rules == rules_after_first_run

        ledger_count_after_second_run = verification_session.execute(
            text("SELECT COUNT(*) FROM schema_migrations WHERE id = :migration_id"),
            {"migration_id": MIGRATION_ID},
        ).scalar_one()
        assert int(ledger_count_after_second_run) == 1


def test_accessory_discount_does_not_require_closed_hundreds():
    product = SimpleNamespace(
        precio=Decimal("1000.00"),
        costo=Decimal("600.00"),
        nombre="Accesorio de prueba",
        sku="ACC-ROUNDING",
        categoria="accesorio",
    )
    item = SimpleNamespace(
        product=product,
        precio_unitario=Decimal("980.00"),
        es_regalo_promocion=False,
    )
    user = SimpleNamespace(is_superuser=False)

    try:
        enforce_sale_price_policy([item], current_user=user)
    except HTTPException as exc:  # pragma: no cover - assertion gives clearer failure
        pytest.fail(f"El accesorio no debe heredar el redondeo de celulares: {exc.detail}")


def test_pricing_policy_migration_converts_legacy_usd_order_once(db_session: Session):
    from app.models import Location, Order, OrderItem, Product

    location = Location(nombre="Migracion USD", direccion="Prueba", active=True)
    profile = SalesProfile(
        name="Perfil USD historico",
        slug="perfil-usd-historico",
        tipo="humano",
        canales='["tienda"]',
        active=True,
        configuracion='{"exchange_rate": 24.50}',
    )
    product = Product(
        sku="USD-MIG-001",
        nombre="Telefono USD historico",
        categoria="celular",
        marca="Test",
        modelo="USD",
        condicion="nuevo",
        precio=Decimal("100.00"),
        costo=Decimal("60.00"),
        moneda="USD",
        activo=True,
    )
    db_session.add_all([location, profile, product])
    db_session.flush()
    order = Order(
        sales_profile_id=profile.id,
        source_location_id=location.id,
        customer_name="Cliente historico",
        customer_phone="99999999",
        canal="tienda",
        metodo_pago="efectivo",
        payment_breakdown='[{"method":"efectivo","amount":100.0}]',
        financing_details='{"down_payment":20.0,"financed_amount":80.0,"monthly_payment":20.0,"surcharge":0.0}',
        total=Decimal("100.00"),
        estado="completada",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderItem(
        order_id=order.id,
        product_id=product.id,
        cantidad=1,
        precio_unitario=Decimal("100.00"),
        costo_unitario=Decimal("60.00"),
        es_regalo_promocion=False,
    ))
    db_session.commit()
    order_id = order.id
    engine = db_session.get_bind()

    assert run_pricing_policy_migration(bind=engine) is True
    with engine.connect() as conn:
        migrated = conn.execute(text(
            "SELECT o.total, o.payment_breakdown, o.financing_details, "
            "oi.precio_unitario, oi.costo_unitario "
            "FROM orders o JOIN order_items oi ON oi.order_id=o.id WHERE o.id=:id"
        ), {"id": order_id}).mappings().one()
        assert Decimal(str(migrated["total"])) == Decimal("2450.00")
        assert Decimal(str(migrated["precio_unitario"])) == Decimal("2450.00")
        assert Decimal(str(migrated["costo_unitario"])) == Decimal("1470.00")
        assert '"amount": 2450.0' in migrated["payment_breakdown"]
        assert '"down_payment": 490.0' in migrated["financing_details"]
        assert conn.execute(
            text("SELECT COUNT(*) FROM schema_migrations WHERE id=:id"),
            {"id": ORDER_CURRENCY_MIGRATION_ID},
        ).scalar_one() == 1

    assert run_pricing_policy_migration(bind=engine) is True
    with engine.connect() as conn:
        again = conn.execute(text(
            "SELECT o.total, oi.precio_unitario, oi.costo_unitario "
            "FROM orders o JOIN order_items oi ON oi.order_id=o.id WHERE o.id=:id"
        ), {"id": order_id}).mappings().one()
        assert Decimal(str(again["total"])) == Decimal("2450.00")
        assert Decimal(str(again["precio_unitario"])) == Decimal("2450.00")
        assert Decimal(str(again["costo_unitario"])) == Decimal("1470.00")
