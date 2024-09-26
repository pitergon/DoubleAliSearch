import asyncio
from unittest.mock import MagicMock

import pytest
import redis.asyncio as redis
from app.search_engine import SearchEngine

session_id = "0fb9617a-1676-4f6e-8f2a-b908038fbf14"
search_uuid = "ce4203b5-dfd7-492b-bf75-9248058537d5"

@pytest.fixture
def redis_client():
    redis_client = redis.from_url("redis://localhost:6379")
    try:
        yield redis_client
    finally:
        # asyncio.run(redis_client.aclose())
        redis_client.aclose()

@pytest.fixture
def search_engine(redis_client):

    engine = SearchEngine(session_id, search_uuid, redis_client)
    engine.max_page = 1
    return engine


@pytest.mark.asyncio
async def test_intersection_in_global_search(search_engine):
    result = await search_engine.intersection_in_global_search([("7260ac",), ("DW5823e",)])
    assert isinstance(result, dict)
