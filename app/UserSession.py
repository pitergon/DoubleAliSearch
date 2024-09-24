import uuid

import aioredis


class UserSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.data = {}

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value):
        self.data[key] = value

    def clear(self):
        self.data.clear()


class RedisUserSession:
    def __init__(self, redis: aioredis.Redis, session_id: str):
        self.redis = redis
        self.session_id = session_id

    async def get(self, key: str):
        value = await self.redis.hget(self.session_id, key)
        return value

    async def set(self, key: str, value):
        await self.redis.hset(self.session_id, key, value)

    async def clear(self):
        await self.redis.delete(self.session_id)