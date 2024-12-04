import asyncio
import json
import uuid
from datetime import datetime
from re import search

import psycopg2

from fastapi import Request, APIRouter, Depends, HTTPException, Security
from fastapi.responses import RedirectResponse, HTMLResponse
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.dependecies import get_db, get_redis
from app.models.models import User, Search
from app.schemas.search_form import SearchForm, SearchFormSave
from app.search_engine import SearchEngine
from app.resources import templates

MAX_SEARCH_COUNT = 2
router = APIRouter()

@router.post("/search/start", response_model=None)
async def search_start_endpoint(page_data: SearchForm,
                                request: Request,
                                redis: Redis = Depends(get_redis),
                                current_user: User = Depends(get_current_user)):
    """
    Start the search process

    :param current_user:
    :param redis:
    :param page_data:
    :param request:
    :return:
    """
    active_searches: dict[str, SearchEngine] = request.app.state.active_searches
    user_id = current_user.id
    search_uuid = str(uuid.uuid4())
    search_key = f"{user_id}:{search_uuid}"
    if search_key in active_searches:
        return {"error": True, "messages": "Search is already running"}
    if sum(1 for key in active_searches.keys() if key.startswith(user_id)) >= MAX_SEARCH_COUNT:
        return {"error": True, "messages": "Too many searches running"}
    await create_search_task(active_searches, redis, page_data.queries_list, user_id, search_uuid)
    await redis.set(f"{search_key}:page_data", page_data.model_dump_json())
    return RedirectResponse(f"/search/{search_uuid}", status_code=303)


async def create_search_task(active_searches, redis, queries_list: list[tuple], user_id, search_uuid):
    """
    Creates async background task with search process

    :param active_searches:
    :param redis:
    :param queries_list:
    :param user_id:
    :param search_uuid:
    :return:
    """
    se = SearchEngine(user_id, search_uuid, redis)
    search_task = asyncio.create_task(se.intersection_in_global_search(queries_list))
    se.task = search_task
    search_key = f"{user_id}:{search_uuid}"
    active_searches[search_key] = se

    async def on_finish():
        await redis.set(f"{user_id}:{search_uuid}:is_finished", 1)
        active_searches.pop(search_key, None)

    def callback(_: asyncio.Task):
        # wrapper for async on_finish function
        asyncio.create_task(on_finish())

    search_task.add_done_callback(callback)


@router.post("/search/{search_uuid}/stop")
async def search_stop_endpoint(request: Request, search_uuid: str, current_user: User = Depends(get_current_user)):
    """
    Stop the search process

    :param current_user:
    :param search_uuid:
    :param request:
    :return:
    """
    user_id = current_user.id
    search_key = f"{user_id}:{search_uuid}"
    active_searches = request.app.state.active_searches
    if search_key not in active_searches:
        return {"error": True, "messages": "Search not found"}
    se: SearchEngine = active_searches[search_key]
    await se.add_message("Search stopped by user")
    se.task.cancel()
    return {"messages": "Search stopped by user"}


@router.post("/search/{search_uuid}/save")
async def search_save_endpoint(page_data: SearchFormSave,
                               search_uuid: str,
                               db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    """
    Save search result into DB

    :param current_user:
    :param search_uuid:
    :param page_data:
    :param db:
    :return:
    """

    if not page_data.names_list1 or not page_data.names_list2:
        return {"error": True, "messages": "Names Lists are empty"}

    new_search: Search = Search(**page_data.model_dump())
    new_search.uuid = search_uuid
    new_search.user_id = current_user.id
    try:
        db.add(new_search)
        db.commit()
        db.refresh(new_search)
    except Exception as e:
        db.rollback()
        return {"error": True, "messages": str(e)}

    return {"messages": "Saved successfully"}


async def clear_redis_data(redis, user_id, search_uuid):
    """
    Clear Redis data after search is finished and client received all messages, results and is_finished flag
    Initiated only after AJAX request for search messages
    :param redis:
    :param user_id:
    :param search_uuid:
    :return:
    """
    await redis.delete(
        f"{user_id}:{search_uuid}:messages",
        f"{user_id}:{search_uuid}:results",
        f"{user_id}:{search_uuid}:is_finished"
    )


@router.get("/search/{search_uuid}/messages")
async def get_search_messages_endpoint(request: Request,
                                       search_uuid: str,
                                       redis: Redis = Depends(get_redis),
                                       current_user: User = Depends(get_current_user)):
    """
    Return messages as answer for AJAX request for certain search

    :param current_user:
    :param redis:
    :param request:
    :param search_uuid:
    :return:
    """
    user_id = current_user.id
    active_searches: dict[str, SearchEngine] = request.app.state.active_searches
    search_key = f"{current_user.id}:{search_uuid}"
    messages = await get_messages(redis, user_id, search_uuid)
    response = {"messages": messages}
    results = await get_results(redis, user_id, search_uuid)
    if results:
        response["results"] = results
    if await check_finished(redis, user_id, search_uuid):
        response["search_finished"] = True
        await clear_redis_data(redis, user_id, search_uuid)
    if not messages and not results and search_key not in active_searches:
        response["error"] = True
        response["messages"] = "Search not found"
    return response


@router.get("/search/{search_uuid}", response_class=HTMLResponse)
async def get_active_search_by_id_endpoint(request: Request,
                                           search_uuid: str,
                                           redis: Redis = Depends(get_redis),
                                           current_user: User = Depends(get_current_user)):

    # search can be deleted from active_searches if it is finished, but user still can access the page

    user_id = current_user.id
    search_key = f"{user_id}:{search_uuid}"
    page_data = await redis.get(f"{search_key}:page_data")
    if not page_data:
        raise HTTPException(status_code=404, detail=f"Search data '{search_uuid}' is not found in storage. ")
    page_data = json.loads(page_data)
    return templates.TemplateResponse(request, "search.j2", {
        "names_list1": page_data.get("names_list1"),
        "names_list2": page_data.get("names_list2"),
        "is_active_search": True,
    })


@router.get("/search", response_class=HTMLResponse)
async def get_search_page_endpoint(request: Request, current_user: User = Depends(get_current_user)):
    """
    Main page
    :param request:
    :return:
    """
    return templates.TemplateResponse(request, "search.j2")


async def get_messages(redis, user_id, search_uuid):
    """
    Get messages from Redis

    :param redis:
    :param user_id:
    :param search_uuid:
    :return:
    """

    count_entry = await redis.get(f"{user_id}:{search_uuid}:read_messages_count")
    read_messages_count = int(count_entry) if count_entry else 0
    messages_entries = await redis.lrange(f"{user_id}:{search_uuid}:messages", read_messages_count, -1)
    read_messages_count += len(messages_entries)
    await redis.set(f"{user_id}:{search_uuid}:read_messages_count", read_messages_count)
    return [entry.decode('utf-8') for entry in messages_entries]


async def check_finished(redis, user_id, search_uuid):
    """
    Checks that the search is finished

    :param redis:
    :param user_id:
    :param search_uuid:
    :return:
    """
    entry = await redis.get(f"{user_id}:{search_uuid}:is_finished")
    is_finished = bool(int(entry)) if entry else False
    return is_finished


async def get_results(redis, user_id, search_uuid):
    """
    Get search results from Redis

    :param redis:
    :param user_id:
    :param search_uuid:
    :return:
    """
    results_entries = await redis.hgetall(f"{user_id}:{search_uuid}:results")
    results = {key.decode('utf-8'): json.loads(value.decode('utf-8')) for key, value in results_entries.items()}
    return results
