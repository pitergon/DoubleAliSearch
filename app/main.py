
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request
from starlette.responses import HTMLResponse
from starlette.datastructures import State
import uuid

from app.dependecies import get_redis
from app.search_engine import SearchEngine
from app.routers import history, search
from app.resources import BASE_DIR, static_files, templates

load_dotenv(os.path.join(BASE_DIR, '.env'))

app = FastAPI()
if not app.state:
    app.state = State()

app.mount("/static", static_files, name="static")
app.include_router(search.router, tags=["search"], dependencies=[Depends(get_redis)])
app.include_router(history.router, tags=["history"])

app.state.background_tasks = set()


@app.get("/", response_class=HTMLResponse)
async def index_endpoint(request: Request):
    """
    Main page
    :param request:
    :return:
    """
    return templates.TemplateResponse("search.html", {"request": request})


@app.middleware("http")
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


def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


async def get_user_data(session_id):
    return {"session_id": session_id}


@app.on_event("startup")
async def startup_event():
    active_searches: dict[str, SearchEngine] = {}
    app.state.active_searches = active_searches


@app.on_event("shutdown")
async def shutdown_event():
    await get_redis().close()
