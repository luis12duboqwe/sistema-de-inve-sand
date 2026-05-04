#!/usr/bin/env python3
"""
Validador rápido de configuración de canales automáticos (Meta).

Uso:
    python check_channels_config.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Tuple


backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.config_production import prod_settings


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def _print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 72}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^72}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 72}{Colors.RESET}\n")


def _ok(text: str) -> None:
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")


def _warn(text: str) -> None:
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {text}")


def _err(text: str) -> None:
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _value(name: str) -> str:
    raw = getattr(prod_settings, name, "")
    return (raw or "").strip() if isinstance(raw, str) else str(raw)


def _is_set(name: str) -> bool:
    return bool(_value(name))


def _validate_at_least_one(names: Iterable[str]) -> Tuple[bool, List[str]]:
    found = [name for name in names if _is_set(name)]
    return (len(found) > 0, found)


def main() -> int:
    _print_header("VALIDACIÓN DE CONFIGURACIÓN DE CANALES")

    errors: List[str] = []

    print("[1] Webhook verify tokens")
    ok_verify, verify_found = _validate_at_least_one(
        ["META_VERIFY_TOKEN", "WHATSAPP_VERIFY_TOKEN", "MESSENGER_VERIFY_TOKEN", "INSTAGRAM_VERIFY_TOKEN"]
    )
    if ok_verify:
        _ok(f"Verify token configurado ({', '.join(verify_found)})")
    else:
        _err("Falta verify token global o por canal")
        errors.append("verify_token")

    print("\n[2] Perfil IA por defecto")
    ok_profile, profile_found = _validate_at_least_one(
        [
            "CHANNEL_DEFAULT_SALES_PROFILE_SLUG",
            "WHATSAPP_DEFAULT_SALES_PROFILE_SLUG",
            "MESSENGER_DEFAULT_SALES_PROFILE_SLUG",
            "INSTAGRAM_DEFAULT_SALES_PROFILE_SLUG",
        ]
    )
    if ok_profile:
        _ok(f"Perfil IA por defecto configurado ({', '.join(profile_found)})")
    else:
        _err("Falta CHANNEL_DEFAULT_SALES_PROFILE_SLUG o slug por canal")
        errors.append("default_sales_profile")

    print("\n[3] Credenciales de salida (WhatsApp)")
    if _is_set("WHATSAPP_ACCESS_TOKEN") and _is_set("WHATSAPP_PHONE_NUMBER_ID"):
        _ok("WhatsApp listo para responder")
        print(f"    - WHATSAPP_ACCESS_TOKEN: {_mask(_value('WHATSAPP_ACCESS_TOKEN'))}")
        print(f"    - WHATSAPP_PHONE_NUMBER_ID: {_mask(_value('WHATSAPP_PHONE_NUMBER_ID'))}")
    else:
        _warn("WhatsApp incompleto (WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID)")

    print("\n[4] Credenciales de salida (Messenger / Instagram)")
    if _is_set("META_PAGE_ACCESS_TOKEN"):
        _ok("Messenger/Instagram listos para responder")
        print(f"    - META_PAGE_ACCESS_TOKEN: {_mask(_value('META_PAGE_ACCESS_TOKEN'))}")
    else:
        _warn("Falta META_PAGE_ACCESS_TOKEN (Messenger/Instagram no podrán responder)")

    print("\n[5] Seguridad y deduplicación")
    if _is_set("META_APP_SECRET"):
        _ok("Firma webhook habilitada (META_APP_SECRET)")
    else:
        _warn("META_APP_SECRET vacío (firma webhook deshabilitada)")

    ttl = getattr(prod_settings, "CHANNEL_MESSAGE_TTL_SECONDS", 600)
    try:
        ttl_int = int(ttl)
        if ttl_int < 60:
            _warn("CHANNEL_MESSAGE_TTL_SECONDS muy bajo, recomendado >= 60")
        else:
            _ok(f"TTL deduplicación: {ttl_int}s")
    except (TypeError, ValueError):
        _err("CHANNEL_MESSAGE_TTL_SECONDS inválido")
        errors.append("ttl")

    _print_header("RESUMEN")
    if errors:
        _err(f"Configuración incompleta: {', '.join(errors)}")
        print("\nSiguiente paso:")
        print("  1) Copiar backend/.env.example.channels a backend/.env")
        print("  2) Completar variables faltantes")
        print("  3) Ejecutar de nuevo: python check_channels_config.py")
        return 1

    _ok("Configuración base válida para conectar canales automáticos")
    print("\nSiguiente paso:")
    print("  1) Configurar webhook callback en Meta Developer")
    print("  2) Reiniciar backend")
    print("  3) Enviar un mensaje real y validar respuesta automática")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
