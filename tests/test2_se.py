import pytest
from unittest.mock import AsyncMock
from app.search_engine import SearchEngine


@pytest.fixture
def search_engine():
    # Подготовка данных
    session_id = "0fb9617a-1676-4f6e-8f2a-b908038fbf14"
    search_uuid = "ce4203b5-dfd7-492b-bf75-9248058537d5"

    # Создаем мок Redis
    redis_mock = AsyncMock()

    # Создаем экземпляр SearchEngine с мокированным Redis
    return SearchEngine(session_id, search_uuid, redis_mock)


@pytest.mark.asyncio
async def test_intersection_in_global_search(search_engine):
    # Мокаем результат вызова rpush
    search_engine.redis.rpush.return_value = 1  # Например, количество добавленных элементов

    # Выполняем тестируемую функцию
    result = await search_engine.intersection_in_global_search([("7260ac",), ("DW5823e",)])

    # Проверяем, что rpush был вызван
    assert search_engine.redis.rpush.called

    # Можно добавить проверку, что rpush был вызван с ожидаемыми аргументами
    # Пример: await search_engine.redis.rpush.assert_called_with(f"{session_id}:{search_uuid}", "some expected message")

    # Проверяем, что результат соответствует ожидаемому (измените на реальные ожидания)
    assert result is not None  # Замените на конкретные проверки, если есть ожидания по результату
