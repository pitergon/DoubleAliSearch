
import json
import math
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

import psycopg2
from psycopg2.extras import DictCursor
import asyncio
from redis.asyncio import Redis
import uuid
from app.models.search_model import SearchPageData
from app.search_engine import SearchEngine
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# static files
static_directory = os.path.join(BASE_DIR, 'static')
app.mount("/static", StaticFiles(directory=static_directory), name="static")

# include templates
templates_directory = os.path.join(BASE_DIR, 'templates')
templates = Jinja2Templates(directory=templates_directory)


background_tasks = set()
load_dotenv(os.path.join(BASE_DIR, '.env'))


def get_db_connection():
    return psycopg2.connect(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_DATABASE')
    )


async def get_redis() -> Redis:
    redis_host = os.getenv('REDIS_HOST', 'localhost:6379')
    redis_password = os.getenv('REDIS_PASSWORD', None)
    redis_url = f"redis://{redis_host}"
    redis = await Redis.from_url(redis_url, password=redis_password)
    return redis


def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


async def get_user_data(session_id):
    return {"session_id": session_id}


async def get_messages(session_id, search_uuid):
    redis = app.state.redis
    count_entry = await redis.get(f"{session_id}:{search_uuid}:read_messages_count")
    read_messages_count = int(count_entry) if count_entry else 0
    await redis.rename(f"{session_id}:{search_uuid}:messages", f"{session_id}:{search_uuid}:read_messages")
    messages_entries = await redis.lrange(f"{session_id}:{search_uuid}:messages", read_messages_count, -1)
    read_messages_count += len(messages_entries)
    await redis.set(f"{session_id}:{search_uuid}:read_messages_count", read_messages_count)
    return [entry.decode('utf-8') for entry in messages_entries]


async def get_results(session_id, search_uuid):
    results_entries = await app.state.redis.hgetall(f"{session_id}:{search_uuid}:results")
    return {key.decode('utf-8'): value.decode('utf-8') for key, value in results_entries.items()}


async def check_finished(session_id, search_uuid):
    entry = await app.state.redis.get(f"{session_id}:{search_uuid}:is_finished")
    is_finished = bool(int(entry)) if entry else False
    return is_finished


async def create_search_task(queries_list: list[tuple], session_id, search_uuid):
    search_task = asyncio.create_task(run_search(queries_list, session_id, search_uuid))
    background_tasks.add(search_task)
    search_task.add_done_callback(background_tasks.discard)


async def run_search(queries_list: list[tuple], session_id, search_uuid):
    redis = app.state.redis
    se = SearchEngine(session_id, search_uuid, redis)
    app.state.active_searches.setdefault(session_id, {}).update({search_uuid: se})
    await redis.set(f"{session_id}:{search_uuid}:is_running", 1)
    await redis.set(f"{session_id}:{search_uuid}:stop_flag", 0)
    await redis.set(f"{session_id}:{search_uuid}:is_finished", 0)
    results = await se.intersection_in_global_search(queries_list)
    await redis.hset(f"{session_id}:{search_uuid}:results", **results)


async def stop_search(session_id, search_uuid):
    print(f"Trying to stop {search_uuid}")
    redis = app.state.redis
    await redis.set(f"{session_id}:{search_uuid}:stop_flag", 1)
    await redis.set(f"{session_id}:{search_uuid}:is_finished", 0)
    del app.state.active_searches[session_id][search_uuid]


@app.on_event("startup")
async def startup_event():
    redis: Redis = await get_redis()
    active_searches: dict[str, dict[str, SearchEngine]] = {}
    app.state.redis = redis
    app.state.active_searches = active_searches


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.redis.aclose()


async def add_session_middleware(request: Request, call_next):
    session_id = get_session_id(request)
    if session_id:
        user_data = await get_user_data(session_id)
        request.state.user_data = user_data
    else:
        request.state.user_data = None
    request.state.session_id = session_id
    response = await call_next(request)
    response.set_cookie(key="session_id", value=session_id)
    # set session_id timer
    return response


async def index_endpoint(request: Request):
    # "/"
    return templates.TemplateResponse("search.html", {"request": request})


async def start_search_endpoint(page_data: SearchPageData, request: Request):
    # "/start_search"
    session_id = request.state.session_id
    if session_id not in app.state.active_searches:
        search_uuid = str(uuid.uuid4())
        await create_search_task(page_data.queries_list, session_id, search_uuid)
        return {"messages": "Search started",
                "search_uuid": search_uuid}
    else:
        return {"messages": "Search is already running"}


async def stop_search_endpoint(request: Request, search_uuid):
    # "/stop_search"
    session_id = request.state.session_id
    if not (session_id in app.state.active_searches and search_uuid in app.state.active_searches[session_id]):
        raise HTTPException(status_code=404, detail=f"Search '{search_uuid}' not found.")
    await stop_search(session_id, search_uuid)
    return {"status": "Search stopped by user"}


async def get_messages_endpoint(request: Request, search_uuid: str):
    # "/get_messages"
    session_id = request.state.session_id
    messages = await get_messages(session_id, search_uuid)
    response = {"messages": messages}
    results = await get_results(session_id, search_uuid)
    if results:
        response["results"] = results
    if await check_finished(session_id, search_uuid):
        response["search_finished"] = True
    return response


async def search_id_endpoint(request: Request, search_id):
    # "/search/{search_uuid}"

    query = """
    SELECT  messages, results, names_list1, names_list2
    FROM history 
    WHERE search_uuid = %s
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (search_id,))
            result = cursor.fetchone()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"Database error: {e}")
    finally:
        connection.close()

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


async def save_search_endpoint(page_data: SearchPageData):
    if not page_data.list1 or not page_data.list2:
        return {"error": "Both lists must have at least one item."}
    postgres_insert_query = """
    INSERT INTO history (messages, results, names_list1, names_list2) 
    VALUES (%s,%s,%s,%s) 
    RETURNING search_uuid
    """
    values = (page_data.messages, json.dumps(page_data.results), page_data.list1, page_data.list2)
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(postgres_insert_query, values)
            last_inserted_id = cursor.fetchone()[0]
            connection.commit()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"Database error: {e}")
    finally:
        connection.close()
    return {"messages": "Saved successfully",
            "url": f"/search/{last_inserted_id}",
            }


async def history_endpoint(request: Request, page: Optional[int] = 1, limit: Optional[int] = 5):
    query = """
    SELECT 
        search_id, 
        created_at, 
        names_list1, 
        names_list2,
        (SELECT COUNT(*) 
            FROM json_object_keys(results) AS keys) AS results_number
    FROM history
    ORDER BY created_at DESC
    LIMIT %s 
    OFFSET %s;
    """
    query_total_count = """
    SELECT COUNT(*) AS total_count 
    FROM history;
    """
    total_records = 0

    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query_total_count)
            total_records = cursor.fetchone()['total_count']
            total_pages = math.ceil(total_records / limit)
            if page > total_pages:
                page = total_pages
            offset = (page - 1) * limit
            cursor.execute(query, (limit, offset))
            history = cursor.fetchall()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"Database error: {e}")
    finally:
        connection.close()

    for record in history:
        record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    pagination = {}

    if total_pages > 1:
        pagination["current_page"] = page
        if page > 1:
            pagination["first"] = 1
        if page > 2:
            pagination["prev"] = page - 1
        if page < total_pages - 1:
            pagination["next"] = page + 1
        if page < total_pages:
            pagination["last"] = total_pages

    return templates.TemplateResponse("history.html", {
        "request": request,
        "history": history,
        "pagination": pagination,
        "current_page": page,
        "total_pages": total_pages,
        "total_records": total_records,
    })


# Define routes
app.middleware("http")(add_session_middleware)
app.get("/", response_class=HTMLResponse)(index_endpoint)
app.post("/start_search")(start_search_endpoint)
app.post("/stop_search")(stop_search_endpoint)
app.get("/get_messages/{search_uuid}")(get_messages_endpoint)
app.get("/search/{search_id}", response_class=HTMLResponse)(search_id_endpoint)
app.get("/history", response_class=HTMLResponse)(history_endpoint)
app.get("/history/{page}", response_class=HTMLResponse)(history_endpoint)
app.post("/save_search")(save_search_endpoint)
