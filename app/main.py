import asyncio

#from dotenv import load_dotenv
#load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.responses import HTMLResponse
from starlette.datastructures import State
import uuid

from app.resources import static_files, templates
from app.dependecies import get_redis
from app.search_engine import SearchEngine
from app.routers import history, search, users

app = FastAPI()
if not app.state:
    app.state = State()
active_searches: dict[str, SearchEngine] = {}
app.state.active_searches = active_searches

app.mount("/static", static_files, name="static")
app.include_router(search.router, tags=["search"])
app.include_router(history.router, tags=["history"])

app.include_router(users.router, tags=["users"])


@app.get("/", response_class=HTMLResponse)
async def index_endpoint(request: Request):
    """
    Main page
    :param request:
    :return:
    """

    return templates.TemplateResponse("search.j2", {"request": request, })


@app.get("/test", response_class=HTMLResponse)
async def index_endpoint(request: Request):
    """
    Main page
    :param request:
    :return:
    """
    print(request.headers)
    return templates.TemplateResponse("test.j2", {"request": request, })


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, e: HTTPException):
    error_details = e.detail if e.detail else "An error occurred"
    return templates.TemplateResponse(
        "error.j2",
        {
            "request": request,
            "error_details": error_details,
            "status_code": e.status_code,
        },
        status_code=e.status_code
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, e: ValidationError):
    error_details = [error.get('ctx', {}).get('reason', 'Unknown error') for error in e.errors()]
    return templates.TemplateResponse(
        "error.j2",
        {
            "request": request,
            "error_details": error_details,
            "status_code": 400,
        },
        status_code=400,
    )


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


@app.middleware("http")
async def add_token_to_header(request: Request, call_next):
    access_token = request.cookies.get("access_token")
    if access_token:
        #request.headers["Authorization"] = access_token
        request.headers.__dict__["_list"].append((b"authorization", access_token.encode()))
    response = await call_next(request)
    return response


def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


async def get_user_data(session_id):
    return {"session_id": session_id}


async def scheduled_redis_clear_task():
    redis = await get_redis()
    while True:
        await asyncio.sleep(86400)
        await redis.delete_incomplete_searches()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_redis_clear_task())


@app.on_event("shutdown")
async def shutdown_event():
    await get_redis().close()
