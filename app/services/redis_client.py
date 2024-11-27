import os
from typing import Optional
import redis.asyncio as redis


class RedisClient:
    """
    Singleton class for Redis connection
    """
    _instance: Optional["RedisClient"] = None

    def __init__(self):
        self._redis = None
        self.init_redis()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init_redis(self):
        if self._redis is None:
            redis_host = os.getenv('REDIS_HOST', 'localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_url = f"redis://{redis_host}"
            self._redis = redis.from_url(redis_url, password=redis_password)

    def get_redis(self):
        if not self._redis:
            raise Exception("Redis not initialized")
        return self._redis

    async def close(self):
        if self._redis:
            await self._redis.aclose()
            self._redis = None
