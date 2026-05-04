#!/usr/bin/env python3
"""
Script para cargar credenciales de prueba en perfiles de venta.

Este script puebla los campos channel_integrations en cada SalesProfile
con credenciales realistas (pero ficticias) para propósitos de demostración
y testing.

Uso:
    python seed_channel_credentials.py              # Mostrar estado actual
    python seed_channel_credentials.py --populate   # Cargar credenciales de prueba
    python seed_channel_credentials.py --clear      # Limpiar credenciales
    python seed_channel_credentials.py --generate   # Generar nuevos tokens aleatorios
"""

import json
import argparse
import random
import string
from typing import Dict, cast
from app.database import SessionLocal
from app.models import SalesProfile


ChannelCredentialsMap = Dict[str, Dict[str, str]]
ChannelIntegrationsConfig = Dict[str, ChannelCredentialsMap]


def _parse_profile_config(raw_config: object) -> ChannelIntegrationsConfig:
    raw_text = str(raw_config or "").strip()
    if not raw_text:
        return {"channel_integrations": {}}

    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            parsed_dict = cast(Dict[str, object], parsed)
            channel_integrations = parsed_dict.get("channel_integrations")
            if isinstance(channel_integrations, dict):
                normalized_integrations: ChannelCredentialsMap = {}
                channel_integrations_dict = cast(Dict[object, object], channel_integrations)
                for channel, creds in channel_integrations_dict.items():
                    if isinstance(channel, str) and isinstance(creds, dict):
                        creds_dict = cast(Dict[object, object], creds)
                        normalized_integrations[channel] = {
                            str(key): str(value)
                            for key, value in creds_dict.items()
                            if isinstance(key, str) and value is not None
                        }
                return {"channel_integrations": normalized_integrations}
            return cast(ChannelIntegrationsConfig, parsed_dict)
    except (TypeError, json.JSONDecodeError):
        pass

    return {"channel_integrations": {}}


def generate_test_token(prefix: str = "test", length: int = 32) -> str:
    """Genera un token aleatorio realista para pruebas."""
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return f"{prefix}_{random_part}"


def generate_test_phone_number_id() -> str:
    """Genera un phone_number_id que parece válido para WhatsApp."""
    return ''.join(random.choices(string.digits, k=15))


def generate_test_page_id() -> str:
    """Genera un page_id que parece válido para Facebook Messenger."""
    return ''.join(random.choices(string.digits, k=18))


def generate_test_instagram_account_id() -> str:
    """Genera un instagram_account_id que parece válido."""
    return ''.join(random.choices(string.digits, k=15))


def get_channel_credentials(canales: str) -> ChannelIntegrationsConfig:
    """
    Genera credenciales de prueba basadas en los canales seleccionados.
    
    Args:
        canales: String delimitado por comas con nombres de canales (whatsapp, facebook, instagram)
    
    Returns:
        Dict con estructura channel_integrations lista para serializar a JSON
    """
    integrations: ChannelCredentialsMap = {}
    
    if not canales:
        return {"channel_integrations": integrations}
    
    canal_list = [c.strip().lower() for c in canales.split(",")]
    
    if "whatsapp" in canal_list:
        integrations["whatsapp"] = {
            "phone_number_id": generate_test_phone_number_id(),
            "access_token": generate_test_token("EAAv"),
            "verify_token": generate_test_token("verify"),
        }
    
    if "facebook" in canal_list or "messenger" in canal_list:
        integrations["messenger"] = {
            "page_id": generate_test_page_id(),
            "page_access_token": generate_test_token("EAAv"),
            "verify_token": generate_test_token("verify"),
        }
    
    if "instagram" in canal_list:
        integrations["instagram"] = {
            "instagram_account_id": generate_test_instagram_account_id(),
            "access_token": generate_test_token("EAAv"),
            "verify_token": generate_test_token("verify"),
        }
    
    return {"channel_integrations": integrations}


def show_current_status():
    """Muestra el estado actual de credenciales en todos los perfiles."""
    db = SessionLocal()
    try:
        profiles = db.query(SalesProfile).filter(SalesProfile.active == True).all()
        
        if not profiles:
            print("⚠ No hay perfiles de venta activos en la base de datos.")
            return
        
        print("\n" + "="*80)
        print("ESTADO ACTUAL DE CREDENCIALES DE CANALES")
        print("="*80)
        
        for profile in profiles:
            config = _parse_profile_config(cast(object, profile.configuracion))
            integrations = config.get("channel_integrations", {})
            
            profile_name = str(profile.name)
            profile_slug = str(profile.slug)
            profile_tipo = str(profile.tipo)
            canales_raw = str(cast(object, profile.canales) or "").strip()

            print(f"\n📱 Perfil: {profile_name} (slug: {profile_slug})")
            print(f"   Tipo: {profile_tipo}")
            print(f"   Canales configurados: {canales_raw or 'Ninguno'}")
            
            if not integrations:
                print("   ⚠ Sin credenciales configuradas")
            else:
                for channel, creds in integrations.items():
                    required_fields = {
                        "whatsapp": ["phone_number_id", "access_token"],
                        "messenger": ["page_id", "page_access_token"],
                        "instagram": ["instagram_account_id", "access_token"],
                    }
                    
                    present = required_fields.get(str(channel), [])
                    status = "✓ Listo" if all(creds.get(f) for f in present) else "⚠ Incompleto"
                    print(f"   {status} {str(channel).upper()}: {len(integrations.get(str(channel), {}))} campos")
        
        print("\n" + "="*80)
        db.close()
    except Exception as e:
        print(f"❌ Error al mostrar estado: {e}")
        db.close()


def populate_credentials():
    """Carga credenciales de prueba en todos los perfiles activos."""
    db = SessionLocal()
    try:
        profiles = db.query(SalesProfile).filter(SalesProfile.active == True).all()
        
        if not profiles:
            print("⚠ No hay perfiles de venta activos para pobluar")
            return
        
        print("\n" + "="*80)
        print("CARGANDO CREDENCIALES DE PRUEBA")
        print("="*80)
        
        updated_count = 0
        for profile in profiles:
            canales_raw = str(cast(object, profile.canales) or "").strip()
            if not canales_raw:
                print(f"\n⚠ {str(profile.name)}: Sin canales configurados, saltando...")
                continue
            
            # Generar nuevas credenciales
            new_config = get_channel_credentials(canales_raw)
            
            # Preservar otras configuraciones si existen
            existing_config = _parse_profile_config(cast(object, profile.configuracion))
            existing_config.update(new_config)
            
            # Guardar
            cast(object, profile).__setattr__("configuracion", json.dumps(existing_config))
            db.add(profile)
            
            print(f"✓ {str(profile.name)}: Credenciales cargadas para {canales_raw}")
            
            # Mostrar detalles
            integrations = new_config.get("channel_integrations", {})
            for channel in integrations:
                print(f"  • {str(channel).upper()}: {len(integrations[str(channel)])} campos configurados")
            
            updated_count += 1
        
        db.commit()
        print(f"\n✓ Actualizado {updated_count} perfil(es)")
        print("="*80 + "\n")
        
        db.close()
    except Exception as e:
        print(f"❌ Error al cargar credenciales: {e}")
        db.rollback()
        db.close()


def clear_credentials():
    """Limpia todas las credenciales de canal."""
    db = SessionLocal()
    try:
        profiles = db.query(SalesProfile).filter(SalesProfile.active == True).all()
        
        if not profiles:
            print("⚠ No hay perfiles activos")
            return
        
        print("\n" + "="*80)
        print("LIMPIANDO CREDENCIALES DE CANAL")
        print("="*80)
        
        cleared_count = 0
        for profile in profiles:
            existing_config = _parse_profile_config(cast(object, profile.configuracion))
            
            # Remover channel_integrations pero preservar otras config
            if "channel_integrations" in existing_config:
                del existing_config["channel_integrations"]
                cast(object, profile).__setattr__("configuracion", json.dumps(existing_config) if existing_config else None)
                db.add(profile)
                print(f"✓ {str(profile.name)}: Credenciales removidas")
                cleared_count += 1
        
        db.commit()
        print(f"\n✓ Limpiado {cleared_count} perfil(es)")
        print("="*80 + "\n")
        
        db.close()
    except Exception as e:
        print(f"❌ Error al limpiar: {e}")
        db.rollback()
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Gestiona credenciales de canal en perfiles de venta para testing"
    )
    parser.add_argument(
        "--populate",
        action="store_true",
        help="Cargar credenciales de prueba en todos los perfiles activos"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Limpiar todas las credenciales de canal"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Regenerar credenciales (equivalente a --clear seguido de --populate)"
    )
    
    args = parser.parse_args()
    
    # Por defecto, mostrar estado si no hay argumentos
    if not (args.populate or args.clear or args.generate):
        show_current_status()
        return
    
    if args.generate:
        clear_credentials()
        populate_credentials()
    elif args.populate:
        populate_credentials()
    elif args.clear:
        clear_credentials()


if __name__ == "__main__":
    main()
