from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import SecurityScopes, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.core.jwt_config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from pydantic import ValidationError
import bcrypt
from app.schemas.token import Token, TokenData
from app.models.models import User
from app.dependecies import get_db

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/token",
)


def get_user(username: str, db) -> User:
    """
    Get user by username
    :param username:
    :param db:
    :return:
    """
    user: Optional[User] = db.query(User).filter(User.username == username, User.disabled == False).first()
    return user


def get_user_by_email(email: str, db) -> User:
    """
    Get user by email
    :param email:
    :param db:
    :return:
    """
    user: Optional[User] = db.query(User).filter(User.email == email, User.disabled == False).first()
    return user


def authenticate_user(username: str, password: str, db) -> User:
    """
    Authenticate user
    :param username:
    :param password:
    :param db:
    :return:
    """
    user = get_user(username, db)
    if not user or user.disabled:
        return False
    if not verify_password(password, user.password):
        return False
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: Session = Depends(get_db, use_cache=True)) -> User:
    """
    Get current user from token
    :param token:
    :param db:
    :return:
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        token_data = TokenData(username=username)
    except (JWTError, ValidationError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user = get_user(username=token_data.username, db=db)
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    if user.disabled:
        raise HTTPException(status_code=403, detail="Forbidden: Inactive user")
    return user


def verify_password(plain_password, hashed_password) -> bool:
    """
    Verify password with hashed password
    :param plain_password:
    :param hashed_password:
    :return:
    """
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password_byte_enc)


def get_password_hash(password) -> str:
    """
    Get password hash
    :param password:
    :return:
    """
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    string_password = hashed_password.decode('utf8')
    return string_password
