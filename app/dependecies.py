from app.services.database import get_db as database_get_db
from app.services.redis_client import RedisClient


def get_redis():
    """
    FastAPI dependency to get connection to Redis using singleton class RedisClient.
    :return:
    """
    redis_client = RedisClient()
    return redis_client.get_redis()


def get_db():
    """
    Wrapper for FastAPI dependency to get database connection for unified usage of dependencies
    """
    yield from database_get_db()