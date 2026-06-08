
from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    picture: str | None
    plan: str
    is_admin: bool
    created_at: str


class GoogleCallbackResponse(BaseModel):
    tokens: TokenPair
    user: UserOut
    is_new_user: bool


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters required")
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    plan: str = "free"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

