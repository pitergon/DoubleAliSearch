import uuid

from fastapi import Request, HTTPException
from datetime import timedelta
from jose import ExpiredSignatureError

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.jwt import verify_token, create_access_token


async def refresh_token_middleware(request: Request, call_next):
    if request.url.path in ["/", "/users/login", "/users/register"]:
        return await call_next(request)
    try:
        access_token = request.cookies.get("access_token")
        if access_token:
            verify_token(access_token)
    except ExpiredSignatureError:
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            username = verify_token(refresh_token)
            if not username:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            new_access_token = create_access_token({"sub": username}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
            # request = Request(scope=request.scope, receive=request.receive)
            request._cookies["access_token"] = new_access_token

            response = await call_next(request)

            response.set_cookie("access_token", new_access_token, httponly=True)
            return response
        else:
            raise HTTPException(status_code=401, detail="Missing refresh token") from None
    response = await call_next(request)
    return response


async def add_token_to_header_middleware(request: Request, call_next):
    access_token = request.cookies.get("access_token")
    if access_token:
        access_token = f"Bearer {access_token}"
        request.headers.__dict__["_list"].append((b"authorization", access_token.encode()))
    response = await call_next(request)
    return response


