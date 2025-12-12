from pydantic_settings import BaseSettings
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
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://*.app.github.dev",
        "https://*.github.dev",
        "*"
    ]
    
    # JWT Authentication
    secret_key: str = "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Support both lowercase and uppercase env vars
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
