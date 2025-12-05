from pydantic_settings import BaseSettings
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
    cors_origins: List[str] = ["*"]  # In production, set specific origins
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Support both lowercase and uppercase env vars
        case_sensitive = False


# Global settings instance
settings = Settings()
