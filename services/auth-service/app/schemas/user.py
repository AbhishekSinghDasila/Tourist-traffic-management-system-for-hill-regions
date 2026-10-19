"""
Pydantic schemas (DTOs).

Rule from the blueprint: never return a raw DB model from an API route.
UserPublic deliberately excludes hashed_password. Even if someone adds
a new sensitive field to the User model later, it will NOT leak through
the API unless it's explicitly added here too.
"""
import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import VALID_ROLES

PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str
    email: Optional[EmailStr] = None
    password: str
    role: str = "tourist"
    district: Optional[str] = Field(default=None, max_length=80)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not PHONE_REGEX.match(v):
            raise ValueError("Phone number must be 10-15 digits, optionally prefixed with +")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode("utf-8")) > 72:
            # bcrypt silently truncates beyond 72 bytes — reject instead
            # of accepting a password that doesn't behave as the user expects
            raise ValueError("Password must not exceed 72 bytes")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        # Public registration can only ever create tourist or citizen accounts.
        # police/admin/emergency_team accounts are created by an existing
        # admin through a separate, protected endpoint — never self-service.
        if v not in ("tourist", "citizen"):
            raise ValueError("Self-registration is only allowed for 'tourist' or 'citizen' roles")
        return v


class AdminUserCreate(UserRegister):
    station_id: Optional[str] = Field(default=None, max_length=80)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError("Invalid account role")
        return v


class UserLogin(BaseModel):
    phone: str
    password: str


class UserPublic(BaseModel):
    id: UUID
    name: str
    phone: str
    email: Optional[EmailStr] = None
    role: str
    district: Optional[str] = None
    station_id: Optional[str] = None  # police only

    class Config:
        from_attributes = True


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
