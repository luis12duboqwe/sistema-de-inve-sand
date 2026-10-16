import json
import pytest

from seed_channel_credentials import (
    _assert_demo_only, _merge_test_integrations, _parse_profile_config,
    _without_channel_integrations,
)


def test_credential_utility_preserves_exchange_rate_and_business_policies():
    original = json.dumps({
        "exchange_rate": 24.5,
        "discount_policy": {"max_discount_rate": 0.02},
        "channel_integrations": {"whatsapp": {"access_token": "old"}},
        "additional_config": ["keep", "this"],
    })
    parsed = _parse_profile_config(original)
    assert parsed["exchange_rate"] == 24.5
    result = _merge_test_integrations(
        original,
        {"channel_integrations": {"instagram": {"access_token": "fake"}}},
    )
    assert result["exchange_rate"] == 24.5
    assert result["discount_policy"] == {"max_discount_rate": 0.02}
    assert result["additional_config"] == ["keep", "this"]
    assert result["channel_integrations"] == {"instagram": {"access_token": "fake"}}

    cleared = _without_channel_integrations(json.dumps(result))
    assert "channel_integrations" not in cleared
    assert cleared["exchange_rate"] == 24.5
    assert cleared["discount_policy"] == {"max_discount_rate": 0.02}
    assert cleared["additional_config"] == ["keep", "this"]


def test_fake_channel_credentials_reject_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="producción"):
        _assert_demo_only()
