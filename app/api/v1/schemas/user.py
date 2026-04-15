"""
사용자 API 스키마
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """사용자 기본 스키마"""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """사용자 생성 스키마"""

    pass


class UserUpdate(BaseModel):
    """사용자 업데이트 스키마"""

    user_id: UUID
    email: EmailStr | None = None
    name: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """사용자 응답 스키마"""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
