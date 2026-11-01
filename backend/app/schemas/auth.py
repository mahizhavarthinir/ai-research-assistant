"""
AI Research Assistant — Authentication Schemas
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: str

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    username: str | None = Field(None, min_length=3, max_length=100)
