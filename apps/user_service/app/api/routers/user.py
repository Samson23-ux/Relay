from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Request, Response


from apps.user_service.app.deps import SecurityDep
from shared.schemas.response import SuccessResponse
from shared.core.shared_config import get_global_settings
from apps.user_service.app.core.config import get_user_settings
from shared.shared_deps import UnitOfWorkRepo, CurrUserDep, RequestMetaData
from apps.user_service.app.deps import AuthServiceDep, UserServiceDep, EmailServiceDep
from apps.user_service.app.api.schemas.user import EmailUserResponse, GoogleUserResponse
from apps.user_service.app.api.schemas.auth import (
    Token,
    ResendOtp,
    EmailLogin,
    EmailVerify,
    EmailSignUp,
    SignUpResponse,
    LogoutResponse,
    OtpResendResponse,
)

router = APIRouter()


USER_SETTINGS = get_user_settings()
GLOBAL_SETTINGS = get_global_settings()


@router.post(
    "/auth/signup",
    status_code=201,
    response_model=SuccessResponse[SignUpResponse],
    description=(
        "Sign up with email and password."
        "A verification code is sent to the user's email on completion"
    ),
)
async def sign_up_with_email(
    security: SecurityDep,
    email_login: EmailSignUp,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    request_meta: RequestMetaData,
    email_service: EmailServiceDep,
):
    await auth_service.sign_up_with_email(
        request_meta, email_login, user_service, email_service, security
    )
    return SuccessResponse(
        message=(
            "Sign up completed successfully."
            "Check your email for verification code and instructions"
        )
    )


@router.get(
    "/auth/google",
    status_code=302,
    response_class=RedirectResponse,
    description="Sign in with Google account",
)
async def sign_in_with_google(request: Request, security: SecurityDep):
    redirect_uri = request.url_for("google_callback")
    await security.register_oauth()
    return await security.oauth.google.authorize_redirect(request, redirect_uri)


@router.get(
    "/auth/google/callback",
    status_code=200,
    response_model=SuccessResponse[Token],
    description="Google redirect uri",
)
async def google_callback(
    request: Request,
    response: Response,
    security: SecurityDep,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    request_meta: RequestMetaData,
):
    await security.register_oauth()
    payload: dict = await security.oauth.google.authorize_access_token(request)
    access_token, refresh_token = await auth_service.sign_up_with_google(
        request_meta, payload, user_service, security
    )

    expire_time: int = USER_SETTINGS.REFRESH_TOKEN_EXPIRE_TIME * 24 * 3600

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=expire_time,
        secure=GLOBAL_SETTINGS.ENVIRONMENT == "production",
        samesite="lax",
    )

    return SuccessResponse(data=Token(access_token=access_token))


@router.patch(
    "/auth/verify",
    status_code=200,
    response_model=SuccessResponse[EmailUserResponse],
    description="Verify account by submitting the received otp code",
)
async def verify_account(
    uow: UnitOfWorkRepo,
    email_verify: EmailVerify,
    auth_service: AuthServiceDep,
    request_meta: RequestMetaData,
):
    await auth_service.verify_account(request_meta, uow, email_verify)
    return SuccessResponse(message="User email verified successfully")


@router.post(
    "/auth/verify/resend",
    status_code=201,
    description="Resend verification code",
    response_model=SuccessResponse[OtpResendResponse],
)
async def resend_otp(
    otp_resend: ResendOtp,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    request_meta: RequestMetaData,
    email_service: EmailServiceDep,
):
    await auth_service.resend_otp(request_meta, otp_resend, user_service, email_service)
    return SuccessResponse(
        message="OTP sent successfully. Check your email for instructions"
    )


@router.post(
    "/auth/login",
    status_code=201,
    description="Login with email and password",
    response_model=SuccessResponse[Token],
)
async def login(
    response: Response,
    security: SecurityDep,
    email_login: EmailLogin,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    request_meta: RequestMetaData,
):
    access_token, refresh_token = await auth_service.login(
        request_meta, email_login, user_service, security
    )

    expire_time: int = USER_SETTINGS.REFRESH_TOKEN_EXPIRE_TIME * 24 * 3600

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=expire_time,
        secure=GLOBAL_SETTINGS.ENVIRONMENT == "production",
        samesite="lax",
    )
    return SuccessResponse(
        message="Login completed successfully", data=Token(access_token=access_token)
    )


@router.post(
    "/auth/refresh",
    status_code=201,
    response_model=SuccessResponse[Token],
    description="Create new access token for user with a valid refresh token",
)
async def create_new_token(
    request: Request,
    response: Response,
    security: SecurityDep,
    auth_service: AuthServiceDep,
    request_meta: RequestMetaData,
):
    refresh_token: str = request.cookies.get("refresh_token")
    access_token, refresh_token = await auth_service.create_auth_tokens(
        request_meta, refresh_token, security
    )

    expire_time: int = USER_SETTINGS.REFRESH_TOKEN_EXPIRE_TIME * 24 * 3600

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=expire_time,
        secure=GLOBAL_SETTINGS.ENVIRONMENT == "production",
        samesite="lax",
    )
    return SuccessResponse(
        message="Token created successfully", data=Token(access_token=access_token)
    )


@router.get(
    "/auth/me",
    status_code=200,
    description="Get current active user",
    response_model=SuccessResponse[EmailUserResponse | GoogleUserResponse],
)
async def get_current_user(
    curr_user: CurrUserDep,
    auth_service: AuthServiceDep,
    request_meta: RequestMetaData,
):
    user: EmailUserResponse | GoogleUserResponse = await auth_service.get_current_user(
        request_meta, curr_user
    )
    return SuccessResponse(message="User retrieved successfully", data=user)


@router.post(
    "/auth/logout",
    status_code=201,
    response_model=SuccessResponse[LogoutResponse],
    description="Log out account",
)
async def log_out(
    request: Request,
    security: SecurityDep,
    curr_user: CurrUserDep,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    request_meta: RequestMetaData,
):
    refresh_token: str = request.cookies.get("refresh_token")
    await auth_service.logout(
        request_meta, curr_user, refresh_token, security, user_service
    )
    return SuccessResponse(message="Log out completed successfully")


@router.delete("/auth", status_code=204, description="Delete account permanently")
async def delete_account(
    request: Request,
    security: SecurityDep,
    curr_user: CurrUserDep,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
    request_meta: RequestMetaData,
):
    refresh_token: str = request.cookies.get("refresh_token")
    await auth_service.delete_account(
        request_meta, curr_user, refresh_token, security, user_service
    )
