from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str | List[str] = ["*"]
    allowed_hosts: str | List[str] = ["*"]
    secret_key: str = "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    setup_token: Optional[str] = None
    destructive_operation_token: Optional[str] = None
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_structured: bool = False
    log_to_files: bool = True
    log_directory: str = "./logs"
    log_include_console: bool = True
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None
    sentry_traces_sample_rate: float = 0.0
    sentry_profiles_sample_rate: float = 0.0
    channel_encryption_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

        env_value = (self.environment or "development").strip().lower()
        self.environment = env_value
        self.database_url = (self.database_url or "").strip()
        self.setup_token = (self.setup_token or "").strip() or None
        self.destructive_operation_token = (
            (self.destructive_operation_token or "").strip() or None
        )

        if not self.database_url:
            if env_value == "production":
                raise ValueError(
                    "DATABASE_URL es obligatorio en producción. Ejemplo: "
                    "postgresql+psycopg2://user:pass@host:5432/inventory_db"
                )
            self.database_url = "sqlite:///./inventory.db"

        database_url_lower = self.database_url.lower()
        if env_value == "production":
            if not database_url_lower.startswith("postgresql"):
                raise ValueError(
                    "Solo PostgreSQL está soportado en producción. "
                    "Usa un DATABASE_URL con prefijo 'postgresql'."
                )
        elif not (
            database_url_lower.startswith("postgresql")
            or database_url_lower.startswith("sqlite")
        ):
            raise ValueError("DATABASE_URL debe usar PostgreSQL o SQLite.")

        self.sentry_traces_sample_rate = self._normalize_rate(
            self.sentry_traces_sample_rate
        )
        self.sentry_profiles_sample_rate = self._normalize_rate(
            self.sentry_profiles_sample_rate
        )

        if env_value != "production":
            return

        if not self.log_structured:
            self.log_structured = True
        if not self.sentry_environment:
            self.sentry_environment = "production"
        if not self.cors_origins or self.cors_origins == ["*"]:
            raise ValueError(
                "CORS_ORIGINS must be a comma-separated list in production; "
                "wildcard '*' is not allowed."
            )
        if not self.allowed_hosts or self.allowed_hosts == ["*"]:
            raise ValueError(
                "ALLOWED_HOSTS must be configured for production. "
                "Provide a comma-separated list of trusted domains."
            )

        secret_key_lower = self.secret_key.lower()
        placeholder_tokens = (
            "your-secret-key",
            "generate_with_openssl",
            "change_me",
        )
        if any(token in secret_key_lower for token in placeholder_tokens):
            raise ValueError(
                "SECRET_KEY must be set for production. Generate a secure key with: "
                "openssl rand -hex 32"
            )
        if not self.setup_token or len(self.setup_token) < 32:
            raise ValueError(
                "SETUP_TOKEN es obligatorio en producción y debe tener al menos "
                "32 caracteres."
            )
        if (
            self.destructive_operation_token
            and len(self.destructive_operation_token) < 32
        ):
            raise ValueError(
                "DESTRUCTIVE_OPERATION_TOKEN debe tener al menos 32 caracteres."
            )


settings = Settings()
