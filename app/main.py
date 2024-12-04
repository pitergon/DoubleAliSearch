import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import ValidationError
from starlette.datastructures import State

from app.resources import static_files, templates
from app.dependecies import get_redis
from app.search_engine import SearchEngine
from app.routers import history, search, users
from app.middleware import refresh_token_middleware, add_token_to_header_middleware
from app.models.models import User
from app.auth import get_current_user


async def scheduled_redis_clear_task():
    """
    Scheduled task to clear incomplete searches from Redis
    :return:
    """
    redis = await get_redis()
    while True:
        await asyncio.sleep(86400)
        await redis.delete_incomplete_searches()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduled_redis_clear_task())
    try:
        yield
    finally:
        task.cancel()
        await redis.close()


app = FastAPI(lifespan=lifespan)
if not app.state:
    app.state = State()
active_searches: dict[str, SearchEngine] = {}
app.state.active_searches = active_searches

app.mount("/static", static_files, name="static")
app.include_router(search.router, tags=["search"])
app.include_router(history.router, tags=["history"])
app.include_router(users.router, tags=["users"])

app.middleware('http')(refresh_token_middleware)
app.middleware('http')(add_token_to_header_middleware)


@app.get("/", response_class=HTMLResponse)
async def index_endpoint(request: Request, current_user: User = Depends(get_current_user)):
    """
    Main page
    :param current_user:
    :param request:
    :return:
    """

    return RedirectResponse(f"/search", status_code=303)


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, e: Exception):
    """
    Helper function to handle 404 errors and return error page
    :param request:
    :param e:
    :return:
    """
    return templates.TemplateResponse(request,
                                      "error.j2",
                                      {"error_details": "Page not found", "status_code": 404},
                                      status_code=404
                                      )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, e: HTTPException):
    """
    Helper function to handle HTTP exceptions and return error page
    :param request:
    :param e:
    :return:
    """
    if e.status_code == 401:
        return RedirectResponse(url="/users/login")
    error_details = e.detail if e.detail else "An error occurred"
    return templates.TemplateResponse(
        request,
        "error.j2",
        {
            "error_details": error_details,
            "status_code": e.status_code,
        },
        status_code=e.status_code
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, e: ValidationError):
    """
    Helper function to handle validation errors and return error page
    :param request:
    :param e:
    :return:
    """
    error_details = [error.get('ctx', {}).get('reason', 'Unknown error') for error in e.errors()]
    return templates.TemplateResponse(
        request,
        "error.j2",
        {
            "error_details": error_details,
            "status_code": 400,
        },
        status_code=400,
    )


