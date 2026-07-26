from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


from apps.user_service.app.api.models.user import UserType, UserRole


class UserBase(BaseModel):
    type: UserType
    role: UserRole = UserRole.USER
    is_active: bool = False
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class GoogleUser(UserBase):
    google_id: Optional[str] = None
    google_email: Optional[EmailStr] = None


class EmailUser(UserBase):
    email: Optional[EmailStr] = None


class UserInDB(GoogleUser, EmailUser):
    hashed_password: Optional[str] = None


class CurrentUser(UserInDB):
    id: UUID
    created_at: datetime


class GoogleUserResponse(GoogleUser):
    id: UUID


class EmailUserResponse(EmailUser):
    id: UUID

