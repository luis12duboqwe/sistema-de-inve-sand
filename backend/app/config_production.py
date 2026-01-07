"""
Configuración extendida para entornos de producción.

Este módulo extiende la configuración base con settings específicos
para producción, incluyendo seguridad, performance y monitoreo.
"""

from app.config import settings
from typing import List, Optional
import os


class ProductionSettings:
    """
    Configuraciones adicionales para entorno de producción.
    """
    
    # ===== SEGURIDAD =====
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    LOGIN_ATTEMPTS_LIMIT: int = int(os.getenv("LOGIN_ATTEMPTS_LIMIT", "5"))
    LOGIN_BLOCK_TIME: int = int(os.getenv("LOGIN_BLOCK_TIME", "15"))
    
    # Headers de seguridad HTTP
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'"
    }
    
    # ===== DATABASE =====
    # Configuración de pool de conexiones para PostgreSQL
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hora
    
    # ===== LOGGING =====
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    ENABLE_FILE_LOGGING: bool = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # "text" o "json"
    
    # ===== BACKUPS =====
    ENABLE_AUTO_BACKUP: bool = os.getenv("ENABLE_AUTO_BACKUP", "false").lower() == "true"
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "./backups")
    BACKUP_SCHEDULE: str = os.getenv("BACKUP_SCHEDULE", "daily")
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    
    # ===== EMAIL =====
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    
    # ===== WHATSAPP (N8N) =====
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    N8N_AUTH_TOKEN: str = os.getenv("N8N_AUTH_TOKEN", "")
    
    # ===== OPENAI =====
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # ===== MONITOREO =====
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    NEW_RELIC_LICENSE_KEY: str = os.getenv("NEW_RELIC_LICENSE_KEY", "")
    
    # ===== REDIS (CACHÉ) =====
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hora
    
    # ===== PERFORMANCE =====
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    
    # ===== FEATURE FLAGS =====
    ENABLE_AI_FEATURES: bool = os.getenv("ENABLE_AI_FEATURES", "true").lower() == "true"
    ENABLE_TRADE_IN: bool = os.getenv("ENABLE_TRADE_IN", "true").lower() == "true"
    ENABLE_FINANCING: bool = os.getenv("ENABLE_FINANCING", "true").lower() == "true"
    ENABLE_IMEI_TRACKING: bool = os.getenv("ENABLE_IMEI_TRACKING", "true").lower() == "true"
    ENABLE_FORECAST_SCHEDULER: bool = os.getenv("ENABLE_FORECAST_SCHEDULER", "false").lower() == "true"
    BUSINESS_INSIGHTS_CACHE_SECONDS: int = int(os.getenv("BUSINESS_INSIGHTS_CACHE_SECONDS", "300"))
    
    # ===== MANTENIMIENTO =====
    MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
    MAINTENANCE_MESSAGE: str = os.getenv("MAINTENANCE_MESSAGE", "Sistema en mantenimiento")
    
    @classmethod
    def is_production(cls) -> bool:
        """Verifica si estamos en entorno de producción"""
        return (not settings.debug) and (settings.environment == "production")
    
    @classmethod
    def validate_production_config(cls) -> List[str]:
        """
        Valida que la configuración de producción sea segura.
        
        Returns:
            Lista de advertencias/errores de configuración
        """
        warnings = []
        
        if cls.is_production():
            # Verificar SECRET_KEY
            if not settings.secret_key or len(settings.secret_key) < 32:
                warnings.append(
                    "CRÍTICO: SECRET_KEY debe ser una clave segura de al menos 32 caracteres"
                )
            
            if "your-secret-key" in (settings.secret_key or ""):
                warnings.append(
                    "CRÍTICO: SECRET_KEY usando valor por defecto. DEBE cambiarse en producción"
                )
            
            # Verificar CORS
            if "*" in settings.cors_origins:
                warnings.append(
                    "SEGURIDAD: CORS_ORIGINS permite todos los orígenes (*). "
                    "Restringir a dominios específicos en producción"
                )
            
            # Verificar base de datos
            if "sqlite" in settings.database_url.lower():
                warnings.append(
                    "PERFORMANCE: SQLite no es recomendado para producción. "
                    "Considerar PostgreSQL o MySQL"
                )
            
            # Verificar logging
            if not cls.ENABLE_FILE_LOGGING:
                warnings.append(
                    "MONITOREO: Logging a archivos deshabilitado. "
                    "Habilitar para trazabilidad en producción"
                )
            
            # Verificar backups
            if not cls.ENABLE_AUTO_BACKUP:
                warnings.append(
                    "BACKUPS: Backups automáticos deshabilitados. "
                    "Altamente recomendado habilitarlos"
                )
            
            # Verificar email
            if not cls.SMTP_HOST or not cls.SMTP_USER:
                warnings.append(
                    "NOTIFICACIONES: Configuración de email incompleta. "
                    "Requerido para notificaciones"
                )
            
            # Verificar OpenAI si AI features están habilitadas
            if cls.ENABLE_AI_FEATURES and not cls.OPENAI_API_KEY:
                warnings.append(
                    "IA: Funcionalidades de IA habilitadas pero OPENAI_API_KEY no configurada"
                )
        
        return warnings


# Instancia singleton de configuración de producción
prod_settings = ProductionSettings()


def check_production_readiness() -> dict:
    """
    Verifica si el sistema está listo para producción.
    
    Returns:
        Dict con estado y advertencias
    """
    warnings = prod_settings.validate_production_config()
    
    return {
        "is_production": prod_settings.is_production(),
        "ready": len(warnings) == 0,
        "warnings": warnings,
        "config": {
            "database": "PostgreSQL/MySQL" if "postgresql" in settings.database_url.lower() or "mysql" in settings.database_url.lower() else "SQLite",
            "logging_enabled": prod_settings.ENABLE_FILE_LOGGING,
            "backups_enabled": prod_settings.ENABLE_AUTO_BACKUP,
            "email_configured": bool(prod_settings.SMTP_HOST),
            "ai_enabled": prod_settings.ENABLE_AI_FEATURES,
            "maintenance_mode": prod_settings.MAINTENANCE_MODE
        }
    }
