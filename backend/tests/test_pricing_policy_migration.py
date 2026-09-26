from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import AIProfileConfig, SalesProfile
from app.schemas import AIConfigSchema
from app.utils.order_pricing import enforce_sale_price_policy
from app.utils.pricing_policy_migration import (
    MIGRATION_ID,
    run_pricing_policy_migration,
)


def test_ai_config_schema_caps_new_configuration_at_three_percent():
    valid = AIConfigSchema(
        sales_profile_id=1,
        system_prompt="Vende sin exceder las reglas.",
        max_discount_rate=0.03,
    )
    assert valid.max_discount_rate == 0.03

    with pytest.raises(ValidationError):
        AIConfigSchema(
            sales_profile_id=1,
            system_prompt="No válido",
            max_discount_rate=0.031,
        )


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
        system_prompt="Prompt histórico",
        max_discount_rate=Decimal("0.1500"),
    )
    db_session.add(historical)
    db_session.commit()

    assert run_pricing_policy_migration() is True
    db_session.expire_all()

    migrated = db_session.query(AIProfileConfig).filter_by(id=historical.id).one()
    assert Decimal(str(migrated.max_discount_rate)) == Decimal("0.0300")

    ledger_count = db_session.execute(
        text("SELECT COUNT(*) FROM schema_migrations WHERE id = :migration_id"),
        {"migration_id": MIGRATION_ID},
    ).scalar_one()
    assert int(ledger_count) == 1

    assert run_pricing_policy_migration() is True
    ledger_count_after_second_run = db_session.execute(
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
