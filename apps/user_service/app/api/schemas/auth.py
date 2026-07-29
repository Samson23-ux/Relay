from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field

from apps.user_service.app.api.models.otp import OtpStatus
from apps.user_service.app.api.models.user import UserType, UserRole


class AuthBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TokenData(AuthBase):
    email: str
    role: UserRole
    user_type: UserType


class Token(AuthBase):
    access_token: str
    token_type: str = "bearer"


class EmailVerify(AuthBase):
    email: str
    otp_code: str


class ResendOtp(AuthBase):
    email: str


class EmailSignUp(AuthBase):
    email: EmailStr
    password: str = Field(..., min_length=8)


class EmailLogin(AuthBase):
    email: EmailStr
    password: str = Field(..., min_length=8)


class OtpInDB(AuthBase):
    otp: str
    user_id: UUID
    status: OtpStatus = "valid"
    expires_at: datetime


class SignUpResponse(BaseModel):
    pass


class OtpResendResponse(BaseModel):
    pass


class LogoutResponse(BaseModel):
    pass
