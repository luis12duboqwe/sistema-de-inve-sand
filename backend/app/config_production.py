"""Configuración extendida para entornos de producción."""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from app.config import settings


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


class ProductionSettings:
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    LOGIN_ATTEMPTS_LIMIT: int = int(os.getenv("LOGIN_ATTEMPTS_LIMIT", "5"))
    LOGIN_BLOCK_TIME: int = int(os.getenv("LOGIN_BLOCK_TIME", "15"))

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }

    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    ENABLE_FILE_LOGGING: bool = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    ENABLE_AUTO_BACKUP: bool = os.getenv("ENABLE_AUTO_BACKUP", "false").lower() == "true"
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "./backups")
    BACKUP_SCHEDULE: str = os.getenv("BACKUP_SCHEDULE", "daily")
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"

    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    N8N_AUTH_TOKEN: str = os.getenv("N8N_AUTH_TOKEN", "")
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_PAGE_ACCESS_TOKEN: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    ADMIN_WHATSAPP_PHONES: List[str] = [
        phone.strip()
        for phone in os.getenv("ADMIN_WHATSAPP_PHONES", "").split(",")
        if phone.strip()
    ]
    MESSENGER_VERIFY_TOKEN: str = os.getenv("MESSENGER_VERIFY_TOKEN", "")
    INSTAGRAM_VERIFY_TOKEN: str = os.getenv("INSTAGRAM_VERIFY_TOKEN", "")
    CHANNEL_DEFAULT_SALES_PROFILE_SLUG: str = os.getenv("CHANNEL_DEFAULT_SALES_PROFILE_SLUG", "")
    WHATSAPP_DEFAULT_SALES_PROFILE_SLUG: str = os.getenv("WHATSAPP_DEFAULT_SALES_PROFILE_SLUG", "")
    MESSENGER_DEFAULT_SALES_PROFILE_SLUG: str = os.getenv("MESSENGER_DEFAULT_SALES_PROFILE_SLUG", "")
    INSTAGRAM_DEFAULT_SALES_PROFILE_SLUG: str = os.getenv("INSTAGRAM_DEFAULT_SALES_PROFILE_SLUG", "")
    CHANNEL_MESSAGE_TTL_SECONDS: int = int(os.getenv("CHANNEL_MESSAGE_TTL_SECONDS", "600"))

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    NEW_RELIC_LICENSE_KEY: str = os.getenv("NEW_RELIC_LICENSE_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))

    WORKERS: int = int(os.getenv("WORKERS", "4"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    MAX_REQUEST_BODY_BYTES: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", "2097152"))

    ENABLE_AI_FEATURES: bool = os.getenv("ENABLE_AI_FEATURES", "true").lower() == "true"
    ENABLE_TRADE_IN: bool = os.getenv("ENABLE_TRADE_IN", "true").lower() == "true"
    ENABLE_FINANCING: bool = os.getenv("ENABLE_FINANCING", "true").lower() == "true"
    ENABLE_IMEI_TRACKING: bool = os.getenv("ENABLE_IMEI_TRACKING", "true").lower() == "true"
    ENABLE_FORECAST_SCHEDULER: bool = os.getenv("ENABLE_FORECAST_SCHEDULER", "false").lower() == "true"
    ENABLE_DESTRUCTIVE_PURGE: bool = os.getenv("ENABLE_DESTRUCTIVE_PURGE", "false").lower() == "true"
    BUSINESS_INSIGHTS_CACHE_SECONDS: int = int(os.getenv("BUSINESS_INSIGHTS_CACHE_SECONDS", "300"))

    MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
    MAINTENANCE_MESSAGE: str = os.getenv("MAINTENANCE_MESSAGE", "Sistema en mantenimiento")

    @classmethod
    def is_production(cls) -> bool:
        return (not settings.debug) and settings.environment == "production"

    @classmethod
    def validate_production_config(cls) -> List[str]:
        warnings: List[str] = []
        if not cls.is_production():
            return warnings

        if not settings.secret_key or len(settings.secret_key) < 32:
            warnings.append("CRÍTICO: SECRET_KEY debe ser una clave segura de al menos 32 caracteres")
        if "your-secret-key" in (settings.secret_key or ""):
            warnings.append("CRÍTICO: SECRET_KEY usando valor por defecto. DEBE cambiarse en producción")
        if not settings.setup_token or len(settings.setup_token) < 32:
            warnings.append("CRÍTICO: SETUP_TOKEN debe estar configurado con al menos 32 caracteres")
        if "*" in settings.cors_origins:
            warnings.append("SEGURIDAD: CORS_ORIGINS permite todos los orígenes (*). Restringir a dominios específicos en producción")
        if not settings.database_url.lower().startswith("postgresql"):
            warnings.append("CRÍTICO: Solo PostgreSQL está soportado. Configura DATABASE_URL con postgresql+psycopg2://...")
        if not cls.ENABLE_FILE_LOGGING:
            warnings.append("MONITOREO: Logging a archivos deshabilitado; se recomienda habilitarlo")
        if not cls.ENABLE_AUTO_BACKUP:
            warnings.append("BACKUPS: Backups automáticos deshabilitados. Deben habilitarse en producción")
        if not cls.SMTP_HOST or not cls.SMTP_USER:
            warnings.append("NOTIFICACIONES: Configuración de email incompleta; funciones de correo no estarán disponibles")
        if cls.ENABLE_AI_FEATURES and not cls.OPENAI_API_KEY:
            warnings.append("IA: Funcionalidades de IA habilitadas pero OPENAI_API_KEY no configurada")
        if cls.ENABLE_DESTRUCTIVE_PURGE:
            if not settings.destructive_operation_token or len(settings.destructive_operation_token) < 32:
                warnings.append("CRÍTICO: La purga destructiva está habilitada sin un token administrativo válido")
            else:
                warnings.append("SEGURIDAD: La purga destructiva está habilitada; manténgala desactivada salvo mantenimiento excepcional")
        return warnings


prod_settings = ProductionSettings()


def check_production_readiness() -> dict:
    warnings = prod_settings.validate_production_config()
    blocking_prefixes = ("CRÍTICO:", "SEGURIDAD:", "BACKUPS:", "IA:")
    blocking_warnings = [warning for warning in warnings if warning.startswith(blocking_prefixes)]

    return {
        "is_production": prod_settings.is_production(),
        "ready": len(blocking_warnings) == 0,
        "warnings": warnings,
        "blocking_warnings": blocking_warnings,
        "config": {
            "database": "PostgreSQL" if "postgresql" in settings.database_url.lower() else "No soportada",
            "logging_enabled": prod_settings.ENABLE_FILE_LOGGING,
            "backups_enabled": prod_settings.ENABLE_AUTO_BACKUP,
            "email_configured": bool(prod_settings.SMTP_HOST),
            "ai_enabled": prod_settings.ENABLE_AI_FEATURES,
            "maintenance_mode": prod_settings.MAINTENANCE_MODE,
            "destructive_purge_enabled": prod_settings.ENABLE_DESTRUCTIVE_PURGE,
        },
    }
