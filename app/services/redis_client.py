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
            # self._redis = redis.from_url(redis_url, password=redis_password)
            self._redis = redis.from_url(redis_url)

    def get_redis(self):
        if not self._redis:
            raise Exception("Redis not initialized")
        return self._redis

    async def close(self):
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def delete_incomplete_searches(self):
        """
        Delete incomplete searches data from Redis. Starts as task every 86400 seconds in asyncio tasks

        :return:
        """
        async for key in self._redis.scan_iter('*'):
            if key.endswith(":is_finished"):
                is_finished = await self._redis.get(key)
                if is_finished == b'1':
                    session_id, search_uuid, _ = key.decode('utf-8').split(":")
                    await self._redis.delete(
                        f"{session_id}:{search_uuid}:messages",
                        f"{session_id}:{search_uuid}:results",
                        f"{session_id}:{search_uuid}:is_finished"
                    )