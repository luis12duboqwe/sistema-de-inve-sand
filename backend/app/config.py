from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, List, Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    These settings can be overridden by creating a .env file in the backend directory.
    """
    # Database
    database_url: str = ""
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # CORS
    cors_origins: List[str] = ["*"]
    allowed_hosts: List[str] = ["*"]
    
    # JWT Authentication
    secret_key: str = "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Environment
    environment: str = "development"

    # Debug
    # Nota: Se usa en varias partes del código (logging_config, config_production, etc.)
    # y se puede sobreescribir con env var DEBUG=true/false.
    debug: bool = False

    # Logging / Observability
    log_level: str = "INFO"
    log_structured: bool = False
    log_to_files: bool = True
    log_directory: str = "./logs"
    log_include_console: bool = True

    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None
    sentry_traces_sample_rate: float = 0.0
    sentry_profiles_sample_rate: float = 0.0
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @classmethod
    def _split_csv(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return value
        return [v.strip() for v in value.split(",") if v.strip()]

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def _parse_csv_list(cls, value: Any) -> Any:
        if isinstance(value, str):
            return cls._split_csv(value)
        return value

    @staticmethod
    def _normalize_rate(value: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, numeric))

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.database_url = (self.database_url or "").strip()

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL es obligatorio y debe apuntar a PostgreSQL. Ejemplo: postgresql+psycopg2://user:pass@host:5432/inventory_db"
            )

        if self.database_url.lower().startswith("sqlite"):
            raise ValueError(
                "SQLite ya no está soportado. Configura DATABASE_URL con PostgreSQL."
            )

        if not self.database_url.lower().startswith("postgresql"):
            raise ValueError(
                "Solo PostgreSQL está soportado. Usa un DATABASE_URL con prefijo 'postgresql'."
            )

        # Normalize environment for consistent checks
        env_value = (self.environment or "development").strip().lower()
        self.environment = env_value

        self.sentry_traces_sample_rate = self._normalize_rate(self.sentry_traces_sample_rate)
        self.sentry_profiles_sample_rate = self._normalize_rate(self.sentry_profiles_sample_rate)

        is_production = env_value == "production"
        if not is_production:
            return

        # En producción forzamos logging estructurado por defecto
        if not self.log_structured:
            self.log_structured = True

        if not self.sentry_environment:
            self.sentry_environment = "production"

        if not self.cors_origins or self.cors_origins == ["*"]:
            raise ValueError(
                "CORS_ORIGINS must be a comma-separated list in production; wildcard '*' is not allowed."
            )

        if not self.allowed_hosts or self.allowed_hosts == ["*"]:
            raise ValueError(
                "ALLOWED_HOSTS must be configured for production. Provide a comma-separated list of trusted domains."
            )

        secret_key_lower = self.secret_key.lower()
        placeholder_tokens = (
            "your-secret-key",
            "generate_with_openssl",
            "change_me",
        )
        if any(token in secret_key_lower for token in placeholder_tokens):
            raise ValueError(
                "SECRET_KEY must be set for production. Generate a secure key with: openssl rand -hex 32"
            )


# Global settings instance
settings = Settings()
