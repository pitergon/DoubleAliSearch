from unittest.mock import MagicMock, AsyncMock

import pytest
import redis.asyncio as redis
from app.search_engine import SearchEngine
import os

session_id = "0fb9617a-1676-4f6e-8f2a-b908038fbf14"
search_uuid = "ce4203b5-dfd7-492b-bf75-9248058537d5"

USE_REAL_REDIS = False
# USE_REAL_REDIS = True


@pytest.fixture()
def anyio_backend():
    return "asyncio"


def read_html_from_file(search: str, page_number: int):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_name = f"{search}-{page_number}.txt"
    file_path = os.path.join(BASE_DIR, "test_data", file_name)
    with open(file_path, 'r', encoding='utf-8') as f:
        print(f"Read file {file_name}")
        html = f.read()
    return html


async def mock_get_html(search: str, page_number: int) -> str:
    try:
        html = read_html_from_file(search, page_number)
    except OSError as e:
        print(e)
        html = ''
    return html


@pytest.fixture()
async def real_redis_client():
    redis_client = redis.from_url("redis://localhost:6379")
    try:
        yield redis_client
    finally:
        await redis_client.aclose()


@pytest.fixture()
async def mock_redis_client():
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    return redis_client


@pytest.fixture()
async def redis_client(real_redis_client, mock_redis_client):
    if USE_REAL_REDIS:
        return real_redis_client
    else:
        return mock_redis_client


@pytest.fixture()
def search_engine(redis_client):
    engine = SearchEngine(session_id, search_uuid, redis_client)
    engine._get_html = MagicMock()
    engine._get_html.side_effect = mock_get_html
    engine.max_page = 3
    engine.enable_pause = False
    return engine


@pytest.mark.anyio
async def test_intersection_in_global_search(search_engine):
    result = await search_engine.intersection_in_global_search([("7260ac",), ("DW5823e",)])
    assert isinstance(result, dict)
