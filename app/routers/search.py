import asyncio
import json
import uuid
from datetime import datetime
from re import search

import psycopg2
from fastapi import Request, APIRouter, Depends, HTTPException, Security
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection
from redis.asyncio import Redis
from starlette.responses import HTMLResponse
from app.dependecies import get_db, get_redis
from app.schemas.search_form import SearchForm, SearchFormSave
from app.search_engine import SearchEngine
from app.resources import templates
from app.try_se import search_uuid

router = APIRouter()


@router.post("/search/start", response_model=None)
async def search_start_endpoint(page_data: SearchForm, request: Request, redis: Redis = Depends(get_redis)):
    """
    Start the search process

    :param redis:
    :param page_data:
    :param request:
    :return:
    """
    active_searches = request.app.state.active_searches
    session_id = request.state.session_id
    search_uuid = page_data.search_uuid
    search_key = f"{session_id}:{search_uuid}"
    if search_key in active_searches:
        return {"messages": "Search is already running"}

    #search_uuid = str(uuid.uuid4())
    # background_tasks = request.app.state.background_tasks
    await create_search_task(active_searches, redis, page_data.queries_list, session_id, search_uuid)
    return {"messages": "Search started",
            "search_uuid": search_uuid}


async def create_search_task(active_searches, redis, queries_list: list[tuple], session_id, search_uuid):
    """
    Creates async background task with search process

    :param active_searches:
    :param redis:
    :param queries_list:
    :param session_id:
    :param search_uuid:
    :return:
    """
    se = SearchEngine(session_id, search_uuid, redis)
    search_task = asyncio.create_task(se.intersection_in_global_search(queries_list))
    se.task = search_task
    search_key = f"{session_id}:{search_uuid}"
    active_searches[search_key] = se

    def on_finish(_: asyncio.Task):
        active_searches.pop(search_key, None)

    search_task.add_done_callback(on_finish)


# async def create_search_task_old(active_searches, background_tasks, redis, queries_list: list[tuple], session_id,
#                                  search_uuid):
#     """
#     Creates async background task with search process
#
#     :param redis:
#
#     :param queries_list:
#     :param session_id:
#     :param search_uuid:
#     :return:
#     """
#     search_task = asyncio.create_task(run_search(active_searches, redis, queries_list, session_id, search_uuid))
#     background_tasks.add(search_task)
#     search_task.add_done_callback(background_tasks.discard)
#
#
# async def run_search_old(active_searches, redis, queries_list: list[tuple], session_id, search_uuid):
#     """
#     Creates search engine instance and starts search
#     :param active_searches:
#     :param redis:
#     :param queries_list:
#     :param session_id:
#     :param search_uuid:
#     :return:
#     """
#     #redis = app.state.redis
#     se = SearchEngine(session_id, search_uuid, redis)
#     active_searches.setdefault(session_id, {}).update({search_uuid: se})
#     await redis.set(f"{session_id}:{search_uuid}:is_running", 1)
#     await redis.set(f"{session_id}:{search_uuid}:stop_flag", 0)
#     await redis.set(f"{session_id}:{search_uuid}:is_finished", 0)
#     results = await se.intersection_in_global_search(queries_list)
#     await redis.hset(f"{session_id}:{search_uuid}:results", **results)


@router.post("/search/stop")
async def search_stop_endpoint(request: Request, search_uuid: str, redis: Redis = Depends(get_redis)):
    """
    Stop the search process

    :param redis:
    :param request:
    :param search_uuid:
    :return:
    """
    session_id = request.state.session_id
    search_key = f"{session_id}:{search_uuid}"
    active_searches = request.app.state.active_searches
    if search_key not in active_searches:
        raise HTTPException(status_code=404, detail=f"Search '{search_uuid}' not found.")
    se: SearchEngine = active_searches[search_key]
    await se.add_message("Search stopped by user")
    se.task.cancel()

    return {"status": "Search stopped by user"}


# async def set_stop_flag(active_searches, redis, session_id, search_uuid):
#     """
#     Create stop flag in Redis and remove search from active searches
#
#     :param redis:
#     :param app: FastAPI app object with state field
#     :param session_id:
#     :param search_uuid:
#     :return:
#     """
#     #print(f"Trying to stop {search_uuid}")
#     #redis = app.state.redis
#     await redis.set(f"{session_id}:{search_uuid}:stop_flag", 1)
#     await redis.set(f"{session_id}:{search_uuid}:is_finished", 0)
#     del active_searches[session_id][search_uuid]


@router.post("/search/save")
async def search_save_endpoint(page_data: SearchFormSave, db: connection = Depends(get_db)):
    """
    Save search result into DB

    :param page_data:
    :param db:
    :return:
    """
    if not page_data.list1 or not page_data.list2:
        return {"error": "Both lists must have at least one item."}
    postgres_insert_query = """
    INSERT INTO history (messages, results, names_list1, names_list2) 
    VALUES (%s,%s,%s,%s) 
    RETURNING search_uuid
    """
    values = (page_data.messages, json.dumps(page_data.results), page_data.list1, page_data.list2)

    try:
        with db.cursor() as cursor:
            cursor.execute(postgres_insert_query, values)
            last_inserted_id = cursor.fetchone()[0]
            db.commit()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"Database error: {e}")

    return {"messages": "Saved successfully",
            "url": f"/search/{last_inserted_id}",
            }


@router.get("/search/{search_uuid}", response_class=HTMLResponse)
async def get_search_by_id_endpoint(request: Request, search_uuid, db: connection = Depends(get_db)):
    """
    Page with results of specified search
    :param request:
    :param search_uuid:
    :param db:
    :return:
    """

    query = """
    SELECT  messages, results, names_list1, names_list2
    FROM history 
    WHERE search_uuid = %s
    """

    try:
        with db.cursor() as cursor:
            cursor.execute(query, (search_uuid,))
            result = cursor.fetchone()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"Database error: {e}")

    if result:
        messages, results, names_list1, names_list2 = result
    else:
        messages = results = names_list1 = names_list2 = None

    return templates.TemplateResponse("search.html", {
        "request": request,
        "messages": json.dumps(messages),
        "results": json.dumps(results),
        "names_list1": names_list1,
        "names_list2": names_list2
    })


@router.get("/search/{search_uuid}/messages/")
async def get_search_messages_endpoint(request: Request, search_uuid: str, redis: Redis = Depends(get_redis)):
    """
    Return messages as answer for AJAX request for certain search

    :param redis:
    :param request:
    :param search_uuid:
    :return:
    """
    session_id = request.state.session_id
    #redis = request.app.state.redis
    messages = await get_messages(redis, session_id, search_uuid)
    response = {"messages": messages}
    results = await get_results(redis, session_id, search_uuid)
    # Здесь нужно проверять все таки наличие результатов, может и флага завершения
    # Потому что после отмены задачи результаты могут быть не записаны
    if results:
        response["results"] = results
    if await check_finished(redis, session_id, search_uuid):
        response["search_finished"] = True
    return response


async def get_messages(redis, session_id, search_uuid):
    """
    Get messages from Redis

    :param redis:
    :param session_id:
    :param search_uuid:
    :return:
    """

    count_entry = await redis.get(f"{session_id}:{search_uuid}:read_messages_count")
    read_messages_count = int(count_entry) if count_entry else 0
    await redis.rename(f"{session_id}:{search_uuid}:messages", f"{session_id}:{search_uuid}:read_messages")
    messages_entries = await redis.lrange(f"{session_id}:{search_uuid}:messages", read_messages_count, -1)
    read_messages_count += len(messages_entries)
    await redis.set(f"{session_id}:{search_uuid}:read_messages_count", read_messages_count)
    return [entry.decode('utf-8') for entry in messages_entries]


async def check_finished(redis, session_id, search_uuid):
    """
    Checks that the search is finished

    :param redis:
    :param session_id:
    :param search_uuid:
    :return:
    """
    entry = await redis.get(f"{session_id}:{search_uuid}:is_finished")
    is_finished = bool(int(entry)) if entry else False
    return is_finished


async def get_results(redis, session_id, search_uuid):
    """
    Get search results from Redis

    :param redis:
    :param session_id:
    :param search_uuid:
    :return:
    """
    results_entries = await redis.hgetall(f"{session_id}:{search_uuid}:results")
    return {key.decode('utf-8'): value.decode('utf-8') for key, value in results_entries.items()}
