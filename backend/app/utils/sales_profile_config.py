"""Helpers for SalesProfile configuration storage and public serialization."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.crypto import decrypt_token, encrypt_token


ENCRYPTED_SECRET_PREFIX = "enc:v1:"
REDACTED_SECRET_VALUE = "***REDACTED***"

_SENSITIVE_KEYS = {
    "access_token",
    "page_access_token",
    "verify_token",
    "auth_token",
    "api_key",
    "app_secret",
    "client_secret",
    "secret",
    "password",
    "smtp_password",
    "webhook_secret",
}


def is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower()
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
        or normalized.endswith("_api_key")
    )


def parse_json_object(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def parse_channels(raw: Optional[str]) -> List[str]:
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        parsed = None

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]

    return [segment.strip() for segment in str(raw).split(",") if segment.strip()]


def _decrypt_value(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(ENCRYPTED_SECRET_PREFIX):
        return decrypt_token(value[len(ENCRYPTED_SECRET_PREFIX):])
    return value


def _walk_config(value: Any, *, mode: str, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {key: _walk_config(item, mode=mode, parent_key=str(key)) for key, item in value.items()}

    if isinstance(value, list):
        return [_walk_config(item, mode=mode, parent_key=parent_key) for item in value]

    if not is_sensitive_key(parent_key):
        return value

    if not isinstance(value, str) or value == "":
        return value

    if mode == "redact":
        return REDACTED_SECRET_VALUE

    if mode == "decrypt":
        return _decrypt_value(value)

    if mode == "encrypt":
        if value == REDACTED_SECRET_VALUE or value.startswith(ENCRYPTED_SECRET_PREFIX):
            return value
        encrypted = encrypt_token(value)
        return f"{ENCRYPTED_SECRET_PREFIX}{encrypted}"

    return value


def _merge_redacted_values(incoming: Any, existing: Any, parent_key: str = "") -> Any:
    if is_sensitive_key(parent_key) and incoming == REDACTED_SECRET_VALUE:
        return existing

    if isinstance(incoming, dict):
        existing_dict = existing if isinstance(existing, dict) else {}
        return {
            key: _merge_redacted_values(value, existing_dict.get(key), str(key))
            for key, value in incoming.items()
            if not (is_sensitive_key(str(key)) and value == REDACTED_SECRET_VALUE and existing_dict.get(key) is None)
        }

    if isinstance(incoming, list):
        existing_list = existing if isinstance(existing, list) else []
        return [
            _merge_redacted_values(value, existing_list[index] if index < len(existing_list) else None, parent_key)
            for index, value in enumerate(incoming)
        ]

    return incoming


def prepare_config_for_storage(config: Optional[Dict[str, Any]], existing_raw: Optional[str] = None) -> Dict[str, Any]:
    incoming_config = config if isinstance(config, dict) else {}
    existing_config = parse_json_object(existing_raw)
    merged_config = _merge_redacted_values(incoming_config, existing_config)
    return _walk_config(merged_config, mode="encrypt")


def parse_sales_profile_config(raw: Optional[str], *, decrypt_secrets: bool = False) -> Dict[str, Any]:
    config = parse_json_object(raw)
    if decrypt_secrets:
        return _walk_config(config, mode="decrypt")
    return config


def sanitize_config_for_response(raw: Optional[str]) -> Dict[str, Any]:
    return _walk_config(parse_json_object(raw), mode="redact")


def extract_channel_integration(raw: Optional[str], channel: str) -> Dict[str, Any]:
    config = parse_sales_profile_config(raw, decrypt_secrets=True)
    integrations = config.get("channel_integrations")
    if not isinstance(integrations, dict):
        return {}

    channel_data = integrations.get(channel)
    return channel_data if isinstance(channel_data, dict) else {}


def serialize_sales_profile(profile: Any) -> Dict[str, Any]:
    return {
        "id": profile.id,
        "name": profile.name,
        "slug": profile.slug,
        "tipo": profile.tipo,
        "active": profile.active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "canales": parse_channels(profile.canales),
        "configuracion": sanitize_config_for_response(profile.configuracion),
    }