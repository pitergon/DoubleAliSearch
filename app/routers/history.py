import math
from typing import Optional

import psycopg2
from fastapi import Request, APIRouter, Depends, HTTPException, Security
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.main import templates
from app.database import get_db
router = APIRouter()

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

    return templates.TemplateResponse("history.html", {
        "request": request,
        "history": history,
        "pagination": pagination,
        "current_page": page,
        "total_pages": total_pages,
        "total_records": total_records,
    })
