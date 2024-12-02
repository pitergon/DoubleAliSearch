from fastapi import Request, APIRouter, Depends, HTTPException, Security, Query
from typing import Annotated, Optional
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_user_by_email,
    oauth2_scheme,
)
from app.core.config import REFRESH_TOKEN_EXPIRE_MINUTES
from app.core.jwt import create_refresh_token, verify_token
from app.resources import templates
from app.schemas.user import UserCreate, UserLogin, UserPasswordReset, UserResponse
from app.schemas.token import Token
from app.models.models import User
from app.dependecies import get_db

ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()


@router.get("/users/register")
async def get_register_page_endpoint(request: Request):
    return templates.TemplateResponse("register.j2", {"request": request, })


@router.post("/users/register", status_code=201)
async def create_user_endpoint(request: Request, registration_form: UserCreate = Depends(UserCreate.as_form),
                               db: Session = Depends(get_db),
                               ):

    user: Optional[User] = (
        db.query(User)
        .filter(
            or_(
                User.username == registration_form.username,
                User.email == registration_form.username,
            )
        )
        .first()
    )
    if user:
        raise HTTPException(
            status_code=400, detail="Username or email already exists"
        )
    new_user: User = User(**registration_form.model_dump(exclude={"confirm_password"}))
    new_user.password = get_password_hash(registration_form.password)
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return templates.TemplateResponse(
        "success.j2", {"request": request,
                       "success_details": "User registered successfully! Now you can <a href='/users/login'>login.</a>"}
    )

@router.get("/users/login")
async def get_login_page_endpoint(request: Request):
    return templates.TemplateResponse("login.j2", {"request": request, })

@router.post("/users/login", response_model=Token)
async def login_for_access_token_endpoint(request: Request,
                                          form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                          db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires,
    )
    # return Token(
    #     access_token=access_token, token_type="bearer", refresh_token=refresh_token
    # )
    response = templates.TemplateResponse("success.j2", {"request": request, "success_details": "Login successful!"})
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True,
                        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie(key="refresh_token", value=f"Bearer {refresh_token}", httponly=True,
                        max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60)

    return response


@router.post("/users/reset-password")
async def reset_password_endpoint(email: str = Query(...), db: Session = Depends(get_db)):
    user = get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    try:
        user.password = None
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"msg": "Password reset successful"}


@router.get("/users/me", response_model=UserResponse)
async def read_users_me_endpoint(
        current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.delete("/users/deactivate/{username}")
async def deactivate_user_endpoint(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user.disabled = True
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"msg": "User deactivated"}


@router.post("/users/token/refresh")
async def refresh_token_endpoint(token: str = Depends(oauth2_scheme)):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": username}, expires_delta=refresh_token_expires
    )

    return Token(
        access_token=access_token, token_type="bearer", refresh_token=refresh_token
    )
