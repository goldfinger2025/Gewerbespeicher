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
    # SECURITY: SECRET_KEY must be set via environment variable in production
    # Generate a secure key with: openssl rand -hex 32
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-OPENSSL-RAND-HEX-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is not the default in production"""
        import warnings
        import os
        if "CHANGE-ME" in v or "your-super-secret" in v:
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "CRITICAL: SECRET_KEY must be set via environment variable in production! "
                    "Generate with: openssl rand -hex 32"
                )
            warnings.warn(
                "Using default SECRET_KEY - set via environment variable for production",
                UserWarning
            )
        return v

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # CORS - accepts comma-separated string or list
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://gewerbespeicher.app",
        "https://gewerbespeicher.vercel.app",
    ]

    # Production domains that should ALWAYS be allowed (merged with ALLOWED_ORIGINS)
    _REQUIRED_ORIGINS: List[str] = [
        "https://gewerbespeicher.vercel.app",
        "https://gewerbespeicher.app",
        "https://www.gewerbespeicher.app",
        "https://gewerbespeicher-production.up.railway.app",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list and merge with required origins"""
        # Parse input
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        else:
            origins = v if v else []

        # Always include required production origins
        required = [
            "https://gewerbespeicher.vercel.app",
            "https://gewerbespeicher.app",
            "https://www.gewerbespeicher.app",
            "https://gewerbespeicher-production.up.railway.app",
        ]

        # Merge and deduplicate
        all_origins = list(set(origins + required))
        return all_origins

    # External Services - Phase 3 Integrations
    HUBSPOT_API_KEY: str = ""
    HUBSPOT_PORTAL_ID: str = ""

    DOCUSIGN_API_KEY: str = ""
    DOCUSIGN_ACCOUNT_ID: str = ""
    DOCUSIGN_USER_ID: str = ""
    DOCUSIGN_PRIVATE_KEY: str = ""
    DOCUSIGN_WEBHOOK_SECRET: str = ""
    DOCUSIGN_PRODUCTION: bool = False

    # Frontend URL for callbacks
    FRONTEND_URL: str = "http://localhost:3000"

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
