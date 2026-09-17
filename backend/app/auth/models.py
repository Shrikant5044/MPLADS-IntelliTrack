from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    MOSPI_OFFICER = "MOSPI_OFFICER"
    DISTRICT_AUTHORITY = "DISTRICT_AUTHORITY"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="Official email address")
    full_name: str = Field(..., description="Full officer name")
    role: UserRole = Field(..., description="Assigned statutory platform role")
    assigned_district: Optional[str] = Field(
        default=None,
        description="Assigned district for DISTRICT_AUTHORITY (e.g. 'District-04'). None for MOSPI_OFFICER/ADMIN.",
    )
    assigned_state: Optional[str] = Field(
        default=None,
        description="Assigned state for geographical context (e.g. 'Maharashtra')",
    )
    is_active: bool = Field(default=True, description="Account active status")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Plaintext password (hashed upon creation)")


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    assigned_district: Optional[str] = None
    assigned_state: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    user_id: str
    created_at: datetime


class UserInDB(UserBase):
    user_id: str
    hashed_password: str
    salt: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
