from app.services.database import get_db_connection
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
    FastAPI dependency to get connection to database.
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
