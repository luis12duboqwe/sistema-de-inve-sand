from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import warnings


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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warn if CORS is wildcard in production.
        if self.environment == "production" and self.cors_origins == ["*"]:
            warnings.warn(
                "CORS está configurado como '*' en production. Configure CORS_ORIGINS para limitar orígenes.",
                UserWarning,
                stacklevel=2,
            )
        # Warn if using default secret key in production
        if self.environment == "production" and "your-secret-key" in self.secret_key:
            warnings.warn(
                "Using default SECRET_KEY in production is insecure! "
                "Generate a new key with: openssl rand -hex 32",
                UserWarning,
                stacklevel=2
            )


# Global settings instance
settings = Settings()
