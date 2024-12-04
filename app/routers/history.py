import json
import math
from re import search
from time import strftime
from typing import Optional

from fastapi import Request, APIRouter, Depends, HTTPException, Security
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from app.auth import get_current_user
from app.models.models import User, Search
from app.resources import templates
from app.dependecies import get_db

router = APIRouter()


@router.get("/history", response_class=HTMLResponse)
@router.get("/history/{page}", response_class=HTMLResponse)
async def history_endpoint(request: Request,
                           page: Optional[int] = 1,
                           limit: Optional[int] = 2,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """
        History page.
    :param current_user:
    :param request:
    :param page:
    :param limit:
    :param db:
    :return:
    """

    total_records = db.query(func.count(Search.id)).filter(Search.user_id == current_user.id).scalar()
    total_pages = math.ceil(total_records / limit)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * limit

    query = text("""
        SELECT
            uuid AS uuid,
            created_at AS created_at,
            names_list1 AS names_list1,
            names_list2 AS names_list2,
            (SELECT COUNT(*)
                FROM json_object_keys(results) AS keys) AS results_number
        FROM searches
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit
        OFFSET :offset;
    """)

    result = db.execute(query, {"user_id": current_user.id,"limit": limit, "offset": offset}).mappings().fetchall()

    searches = []
    for row in result:
        searches.append({
            "uuid": row["uuid"],
            "created_at": row["created_at"].astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "names_list1": row["names_list1"],
            "names_list2": row["names_list2"],
            "results_number": row["results_number"]
        })

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

    # Возврат шаблона с данными
    return templates.TemplateResponse("history.j2", {
        "request": request,
        "searches": searches,
        "pagination": pagination,
        "current_page": page,
        "total_pages": total_pages,
        "total_records": total_records,
    })



@router.get("/history/search/{search_uuid}", response_class=HTMLResponse)
async def get_saved_search_by_id_endpoint(request: Request,
                                          search_uuid: str,
                                          db: Session = Depends(get_db),
                                          current_user: User = Depends(get_current_user)
                                          ):
    """

    :param request:
    :param search_uuid:
    :param db:
    :param current_user:
    :return:
    """

    search = db.query(Search).filter(Search.uuid == search_uuid, Search.user_id == current_user.id).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    return templates.TemplateResponse("search.j2", {
        "request": request,
        "messages": json.dumps(search.messages),
        "results": json.dumps(search.results),
        "names_list1": search.names_list1,
        "names_list2": search.names_list2
    })

# @router.get("/history/search/{search_uuid}", response_class=HTMLResponse)
# async def get_saved_search_by_id_endpoint(request: Request,
#                                           search_uuid: str,
#                                           db: Session = Depends(get_db),
#                                           current_user: User = Depends(get_current_user)
#                                           ):
#     """
#     Page with results of specified search
#     :param current_user:
#     :param request:
#     :param search_uuid:
#     :param db:
#     :return:
#     """
#
#
#
#     query = """
#     SELECT  messages, results, names_list1, names_list2
#     FROM history
#     WHERE search_uuid = %s
#     """
#
#     try:
#         with db.cursor() as cursor:
#             cursor.execute(query, (search_uuid,))
#             result = cursor.fetchone()
#     except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
#         print(f"Database error: {e}")
#
#     if result:
#         messages, results, names_list1, names_list2 = result
#     else:
#         messages = results = names_list1 = names_list2 = None
#
#     return templates.TemplateResponse("search.j2", {
#         "request": request,
#         "messages": json.dumps(messages),
#         "results": json.dumps(results),
#         "names_list1": names_list1,
#         "names_list2": names_list2
#     })
