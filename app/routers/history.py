import json
import math
from typing import Optional

import psycopg2
from fastapi import Request, APIRouter, Depends, HTTPException, Security
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection
from starlette.responses import HTMLResponse
from app.resources import templates
from app.dependecies import get_db

router = APIRouter()


@router.get("/history", response_class=HTMLResponse)
@router.get("/history/{page}", response_class=HTMLResponse)
async def history_endpoint(request: Request,
                           page: Optional[int] = 1,
                           limit: Optional[int] = 5,
                           db: connection = Depends(get_db)):
    """
    Страница истории поиска.
    :param db:
    :param request:
    :param page:
    :param limit:
    :return:
    """
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
    try:
        with db.cursor(cursor_factory=DictCursor) as cursor:
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

    return templates.TemplateResponse("history.j2", {
        "request": request,
        "history": history,
        "pagination": pagination,
        "current_page": page,
        "total_pages": total_pages,
        "total_records": total_records,
    })


@router.get("/history/search/{search_uuid}", response_class=HTMLResponse)
async def get_saved_search_by_id_endpoint(request: Request, search_uuid: str, db: connection = Depends(get_db)):
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

    return templates.TemplateResponse("search.j2", {
        "request": request,
        "messages": json.dumps(messages),
        "results": json.dumps(results),
        "names_list1": names_list1,
        "names_list2": names_list2
    })
