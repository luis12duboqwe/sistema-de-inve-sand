from decimal import Decimal
from types import SimpleNamespace

from app.utils.order_currency import (
    DEFAULT_HNL_PER_USD,
    product_amount_in_hnl,
    resolve_exchange_rate,
)


def test_exchange_rate_reads_modern_sales_profile_config():
    profile = SimpleNamespace(configuracion='{"exchange_rate": 24.75}', settings=None)
    assert resolve_exchange_rate(profile) == Decimal("24.75")


def test_exchange_rate_reads_legacy_profile_settings():
    profile = SimpleNamespace(configuracion=None, settings='{"exchangeRate": 24.25}')
    assert resolve_exchange_rate(profile) == Decimal("24.25")


def test_exchange_rate_falls_back_for_invalid_config():
    profile = SimpleNamespace(configuracion='{"exchange_rate": 0}', settings=None)
    assert resolve_exchange_rate(profile) == DEFAULT_HNL_PER_USD


def test_usd_amount_is_normalized_to_hnl():
    product = SimpleNamespace(moneda="USD")
    assert product_amount_in_hnl(Decimal("100.00"), product, Decimal("24.50")) == Decimal("2450.00")


def test_hnl_amount_is_not_converted():
    product = SimpleNamespace(moneda="HNL")
    assert product_amount_in_hnl(Decimal("100.00"), product, Decimal("24.50")) == Decimal("100.00")
