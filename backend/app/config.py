from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    These settings can be overridden by creating a .env file in the backend directory.
    """
    # Database
    database_url: str = "sqlite:///./inventory.db"
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # CORS
    cors_origins: List[str] = ["*"]
    
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

    # Permitir CORS_ORIGINS como CSV para despliegues
    @classmethod
    def model_validate(cls, value):  # type: ignore[override]
        if isinstance(value, dict) and "cors_origins" in value and isinstance(value["cors_origins"], str):
            value = value.copy()
            value["cors_origins"] = cls._split_csv(value["cors_origins"])
        return super().model_validate(value)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Normalize environment for consistent checks
        env_value = (self.environment or "development").strip().lower()
        self.environment = env_value

        is_production = env_value == "production"
        if not is_production:
            return

        if self.database_url == "sqlite:///./inventory.db":
            raise ValueError(
                "DATABASE_URL must be set for production (e.g., postgresql+psycopg2://user:pass@host:5432/inventory)."
            )

        if not self.cors_origins or self.cors_origins == ["*"]:
            raise ValueError(
                "CORS_ORIGINS must be a comma-separated list in production; wildcard '*' is not allowed."
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
