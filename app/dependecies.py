from app.database import get_db_connection
from redis_client import RedisClient


def get_redis():
    """
    FastAPI-зависимость для получения подключения к Redis, используя singleton-класс RedisClient.
    :return:
    """
    redis_client = RedisClient()
    return redis_client.get_redis()


def get_db():
    """FastAPI-зависимость для получения подключения к базе данных."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
