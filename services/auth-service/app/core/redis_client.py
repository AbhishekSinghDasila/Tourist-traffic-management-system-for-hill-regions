"""
Redis client — used here for JWT blacklisting on logout.
Single connection pool shared across the service.
"""
import redis

from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
