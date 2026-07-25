from apps.user_service.app.main import app
from apps.user_service.app.api import models
from apps.user_service.app.api.routers import user
from apps.user_service.app.api.routers import router
from apps.user_service.app.utils import get_user_email
from apps.user_service.app.api.models.base import Base
from apps.user_service.app.core.security import Security
from apps.user_service.app.api.models.email import Email
from apps.user_service.app.api.repo.otp import OtpRepository
from apps.user_service.app.api.services.otp import OtpService
from apps.user_service.app.worker.celery_app import celery_app
from apps.user_service.app.api.repo.user import UserRepository
from apps.user_service.app.core.config import get_user_settings
from apps.user_service.app.api.models.otp import Otp, OtpStatus
from apps.user_service.app.api.services.auth import AuthService
from apps.user_service.app.api.services.user import UserService
from apps.user_service.app.api.repo.email import EmailRepository
from apps.user_service.app.api.models.user import User, UserType
from apps.user_service.app.api.services.email import EmailService
from apps.user_service.app.api.schemas.email import EmailInDB, EmailBase
from apps.user_service.app.worker.tasks.email import send_verification_email
from apps.user_service.app.worker.services import get_otp_service, get_email_service
from apps.user_service.app.deps import AuthServiceDep, UserServiceDep, EmailServiceDep
from apps.user_service.app.api.schemas.user import (
    UserBase,
    UserInDB,
    EmailUserResponse,
    GoogleUserResponse,
)
from apps.user_service.app.api.schemas.auth import (
    Token,
    OtpInDB,
    AuthBase,
    TokenData,
    ResendOtp,
    EmailLogin,
    EmailVerify,
    EmailSignUp,
    SignUpResponse,
    LogoutResponse,
    OtpResendResponse,
)
from apps.user_service.app.core.exceptions import (
    AuthorizationError,
    AuthenticationError,
    CredentialError,
    UserExistsError,
    InvalidOtpError,
    UserNotFoundError,
)
from apps.user_service.app.deps import get_auth_service, get_security, SecurityDep

__all__ = [
    "app",
    "Otp",
    "Base",
    "User",
    "user",
    "Email",
    "Token",
    "models",
    "router",
    "OtpInDB",
    "UserInDB",
    "AuthBase",
    "UserBase",
    "UserType",
    "Security",
    "ResendOtp",
    "TokenData",
    "OtpStatus",
    "EmailInDB",
    "EmailBase",
    "OtpService",
    "celery_app",
    "EmailLogin",
    "EmailSignUp",
    "EmailVerify",
    "AuthService",
    "UserService",
    "SecurityDep",
    "EmailService",
    "get_security",
    "OtpRepository",
    "UserRepository",
    "SignUpResponse",
    "get_user_email",
    "LogoutResponse",
    "AuthServiceDep",
    "UserServiceDep",
    "get_otp_service",
    "EmailServiceDep",
    "get_email_service",
    "OtpResendResponse",
    "EmailUserResponse",
    "GoogleUserResponse",
    "EmailRepository",
    "AuthorizationError",
    "AuthenticationError",
    "CredentialError",
    "UserExistsError",
    "InvalidOtpError",
    "UserNotFoundError",
    "get_auth_service",
    "get_user_settings",
    "send_verification_email",
]
