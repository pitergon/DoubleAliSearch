from typing import Self

from fastapi import Form, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, root_validator, model_validator


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True,
                              str_strip_whitespace=True,
                              extra="ignore")
    username: str = Field(..., examples=["johnsmith"])
    email: EmailStr = Field(..., examples=["email@example.com"])
    disabled: bool = Field(False, examples=[False])


class UserCreate(UserBase):
    password: str = Field(..., examples=["password"])
    confirm_password: str = Field(..., examples=["password"])

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        return self

    @classmethod
    def as_form(cls,
                username: str = Form(...),
                email: str = Form(...),
                password: str = Form(...),
                confirm_password: str = Form(...),
                ) -> Self:
        return cls(username=username,email=email,password=password,confirm_password=confirm_password)


class UserResponse(UserBase):
    id: int = Field(..., examples=[1])


class UserPasswordReset(UserBase):
    new_password: str = Field(None, examples=["password"])


class UserLogin(UserBase):
    password: str = Field(..., examples=["password"])
