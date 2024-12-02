from pydantic import BaseModel, ConfigDict, Field

class Token(BaseModel):
    model_config = ConfigDict(from_attributes=True,
                              str_strip_whitespace=True,
                              extra="ignore")
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(..., example="bearer")
    refresh_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

class TokenData(BaseModel):
    username: str | None = Field(None, example="user@example.com")
    scopes: list[str] = Field(default_factory=list, example=["read", "write"])


