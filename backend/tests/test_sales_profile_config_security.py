import json

from app.utils.sales_profile_config import (
    ENCRYPTED_SECRET_PREFIX,
    REDACTED_SECRET_VALUE,
    extract_channel_integration,
    parse_sales_profile_config,
    prepare_config_for_storage,
    sanitize_config_for_response,
)


def test_sales_profile_config_encrypts_and_redacts_sensitive_values():
    config = {
        "exchange_rate": 24.5,
        "channel_integrations": {
            "whatsapp": {
                "phone_number_id": "12345",
                "access_token": "wa-secret-token",
                "verify_token": "wa-verify-token",
            }
        },
    }

    stored_config = prepare_config_for_storage(config)

    whatsapp_config = stored_config["channel_integrations"]["whatsapp"]
    assert whatsapp_config["phone_number_id"] == "12345"
    assert whatsapp_config["access_token"].startswith(ENCRYPTED_SECRET_PREFIX)
    assert whatsapp_config["verify_token"].startswith(ENCRYPTED_SECRET_PREFIX)

    raw_config = json.dumps(stored_config)
    decrypted_config = parse_sales_profile_config(raw_config, decrypt_secrets=True)
    assert decrypted_config["channel_integrations"]["whatsapp"]["access_token"] == "wa-secret-token"
    assert decrypted_config["channel_integrations"]["whatsapp"]["verify_token"] == "wa-verify-token"

    public_config = sanitize_config_for_response(raw_config)
    public_whatsapp_config = public_config["channel_integrations"]["whatsapp"]
    assert public_whatsapp_config["phone_number_id"] == "12345"
    assert public_whatsapp_config["access_token"] == REDACTED_SECRET_VALUE
    assert public_whatsapp_config["verify_token"] == REDACTED_SECRET_VALUE


def test_redacted_update_preserves_existing_sensitive_values():
    existing_config = prepare_config_for_storage(
        {
            "channel_integrations": {
                "whatsapp": {
                    "phone_number_id": "old-phone-id",
                    "access_token": "existing-secret",
                }
            }
        }
    )

    updated_config = prepare_config_for_storage(
        {
            "channel_integrations": {
                "whatsapp": {
                    "phone_number_id": "new-phone-id",
                    "access_token": REDACTED_SECRET_VALUE,
                }
            }
        },
        existing_raw=json.dumps(existing_config),
    )

    decrypted_config = parse_sales_profile_config(json.dumps(updated_config), decrypt_secrets=True)
    whatsapp_config = decrypted_config["channel_integrations"]["whatsapp"]
    assert whatsapp_config["phone_number_id"] == "new-phone-id"
    assert whatsapp_config["access_token"] == "existing-secret"


def test_extract_channel_integration_returns_decrypted_credentials():
    stored_config = prepare_config_for_storage(
        {
            "channel_integrations": {
                "messenger": {
                    "page_id": "page-1",
                    "page_access_token": "messenger-secret",
                }
            }
        }
    )

    integration = extract_channel_integration(json.dumps(stored_config), "messenger")

    assert integration == {
        "page_id": "page-1",
        "page_access_token": "messenger-secret",
    }