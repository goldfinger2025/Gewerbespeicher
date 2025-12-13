"""
Redis Cache Configuration
Upstash-compatible async Redis client
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
from functools import wraps

from app.config import settings


class RedisCache:
    """
    Async Redis cache client with Upstash support.
    Handles both local Redis and Upstash (TLS) connections.
    """

    _client: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client instance"""
        if cls._client is None:
            # Upstash uses rediss:// (TLS), local uses redis://
            url = settings.REDIS_URL

            # Connection options
            kwargs = {
                "decode_responses": True,
                "socket_timeout": 5.0,
                "socket_connect_timeout": 5.0,
            }

            # Upstash/Production: Enable SSL
            if url.startswith("rediss://"):
                kwargs["ssl_cert_reqs"] = None  # Upstash handles certs

            cls._client = redis.from_url(url, **kwargs)

        return cls._client

    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            client = await cls.get_client()
            return await client.get(key)
        except Exception:
            return None

    @classmethod
    async def set(
        cls,
        key: str,
        value: Any,
        expire: int = 3600
    ) -> bool:
        """Set value in cache with expiration (default 1 hour)"""
        try:
            client = await cls.get_client()
            if not isinstance(value, str):
                value = json.dumps(value)
            await client.set(key, value, ex=expire)
            return True
        except Exception:
            return False

    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = await cls.get_client()
            await client.delete(key)
            return True
        except Exception:
            return False

    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists"""
        try:
            client = await cls.get_client()
            return await client.exists(key) > 0
        except Exception:
            return False

    @classmethod
    async def get_json(cls, key: str) -> Optional[dict]:
        """Get and parse JSON value from cache"""
        value = await cls.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    @classmethod
    async def health_check(cls) -> bool:
        """Check Redis connection health"""
        try:
            client = await cls.get_client()
            await client.ping()
            return True
        except Exception:
            return False


def cached(expire: int = 3600, prefix: str = "cache"):
    """
    Decorator for caching function results.

    Usage:
        @cached(expire=300, prefix="simulation")
        async def get_simulation(project_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key_parts = [prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = await RedisCache.get_json(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await RedisCache.set(cache_key, result, expire=expire)

            return result
        return wrapper
    return decorator


# Initialize cache on startup
async def init_cache():
    """Initialize Redis connection"""
    await RedisCache.get_client()


# Close cache on shutdown
async def close_cache():
    """Close Redis connection"""
    await RedisCache.close()
