from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserInDB(UserBase):
    id: Optional[str] = Field(alias="_id")
    hashed_password: str
    is_active: bool = True
    role: UserRole = UserRole.USER
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: str
    is_active: bool
    role: UserRole = UserRole.USER
    watchlist: List[str] = []
    profiles: List[dict] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    watchlist: List[str]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int


# ── FR-12: Multi-Profile ───────────────────────────────────────────

class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)
    avatar_url: Optional[str] = None
    maturity_level: str = Field(default="adult", pattern="^(kids|teen|adult)$")


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    maturity_level: Optional[str] = Field(None, pattern="^(kids|teen|adult)$")


class ProfileResponse(BaseModel):
    profile_id: str
    name: str
    avatar_url: Optional[str] = None
    maturity_level: str = "adult"
    created_at: datetime
