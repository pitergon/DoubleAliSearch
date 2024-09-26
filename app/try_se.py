import asyncio

import pytest
from fastapi.testclient import TestClient
from app.search_engine import SearchEngine
from unittest.mock import MagicMock, patch
from redis.asyncio import Redis
# from redis import Redis

session_id = "0fb9617a-1676-4f6e-8f2a-b908038fbf14"
search_uuid = "ce4203b5-dfd7-492b-bf75-9248058537d5"
redis = Redis.from_url("redis://localhost:6379")
# redis.set("session_id:search_uuid:read_messages_count", 99)
# redis.get("session_id:search_uuid:read_messages_count")

se = SearchEngine(session_id, search_uuid, redis)
result = asyncio.run(se.intersection_in_global_search([("7260ac",), ("DW5823e",)]))
print(result)