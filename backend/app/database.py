"""
Database Configuration
SQLAlchemy async setup with PostgreSQL (Neon Serverless Compatible)
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import ssl

from app.config import settings


# Convert sync database URL to async URL
def get_async_database_url() -> str:
    """Convert postgresql:// to postgresql+asyncpg:// and remove incompatible params"""
    url = settings.DATABASE_URL

    # Remove sslmode and channel_binding params (handled via connect_args for asyncpg)
    if "?" in url:
        base_url = url.split("?")[0]
    else:
        base_url = url

    if base_url.startswith("postgresql://"):
        return base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif base_url.startswith("postgres://"):
        return base_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return base_url


def get_engine_kwargs() -> dict:
    """
    Get engine configuration based on environment.
    Neon requires NullPool for serverless and SSL for connections.
    """
    base_kwargs = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
    }

    # Production (Neon Serverless) - use NullPool and SSL
    if settings.ENVIRONMENT == "production":
        return {
            **base_kwargs,
            "poolclass": NullPool,  # Required for serverless
            "connect_args": {
                "ssl": ssl.create_default_context(),
                "server_settings": {
                    "application_name": "gewerbespeicher-api"
                }
            }
        }

    # Development - use connection pooling
    return {
        **base_kwargs,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
    }


# Create async engine
engine = create_async_engine(
    get_async_database_url(),
    **get_engine_kwargs()
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base class for all models
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Usage in endpoints:
        async def endpoint(db: AsyncSession = Depends(get_db)):
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()
