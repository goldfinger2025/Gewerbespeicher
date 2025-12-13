"""
Application Configuration
Uses pydantic-settings for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings loaded from environment variables"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/gewerbespeicher"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Authentication
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # CORS - accepts comma-separated string or list
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://gewerbespeicher.app",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # External Services
    HUBSPOT_API_KEY: str = ""
    DOCUSIGN_API_KEY: str = ""

    # PV Simulation Defaults
    DEFAULT_ELECTRICITY_PRICE: float = 0.30  # EUR/kWh
    DEFAULT_FEED_IN_TARIFF: float = 0.08  # EUR/kWh
    DEFAULT_PV_TILT: float = 30.0  # degrees
    DEFAULT_PV_ORIENTATION: str = "south"

    # Germany Coordinates (for default location)
    DEFAULT_LATITUDE: float = 54.5  # Handewitt area
    DEFAULT_LONGITUDE: float = 9.3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
