import json
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
from app.models.search_model import SearchPageData

router = APIRouter()

# app.post("/start_search")(start_search_endpoint)
# app.post("/stop_search")(stop_search_endpoint)
# app.get("/get_messages/{search_uuid}")(get_messages_endpoint)
# app.get("/search/{search_id}", response_class=HTMLResponse)(search_id_endpoint)


# app.post("/save_search")(save_search_endpoint)


@router.post("/search/start")
async def search_start_endpoint(page_data: SearchPageData, request: Request):
    """
    Start the search process

    :param page_data:
    :param request:
    :return:
    """
    session_id = request.state.session_id
    if session_id not in app.state.active_searches:
        search_uuid = str(uuid.uuid4())
        await create_search_task(page_data.queries_list, session_id, search_uuid)
        return {"messages": "Search started",
                "search_uuid": search_uuid}
    else:
        return {"messages": "Search is already running"}


@router.post("/search/stop")
async def search_stop_endpoint(request: Request, search_uuid):
    """
    Stop the search process

    :param request:
    :param search_uuid:
    :return:
    """
    session_id = request.state.session_id
    if not (session_id in app.state.active_searches and search_uuid in app.state.active_searches[session_id]):
        raise HTTPException(status_code=404, detail=f"Search '{search_uuid}' not found.")
    await stop_search(session_id, search_uuid)
    return {"status": "Search stopped by user"}


@router.get("/search/{search_id}", response_class=HTMLResponse)
async def search_id_endpoint(request: Request, search_id, db: connection = Depends(get_db)):
    """
    Page with results of specified search
    :param request:
    :param search_id:
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
            cursor.execute(query, (search_id,))
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

@router.post("/search/save")
async def search_save_endpoint(page_data: SearchPageData, db: connection = Depends(get_db)):
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
