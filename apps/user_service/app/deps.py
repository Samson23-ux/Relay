from fastapi import Depends
from typing import Annotated


from shared import RedisRepo, DBSession
from apps.user_service import (
    AuthService,
    OtpRepository,
    Security,
    UserRepository,
    UserService,
    EmailRepository,
    EmailService
)


# ------------------- Security dependency ------------------------------ #
async def get_security() -> Security:
    return Security()


SecurityDep = Annotated[Security, Depends(get_security)]


#  ------------------- Repo dependency ----------------------------- #


async def get_otp_repo(session: DBSession) -> OtpRepository:
    return OtpRepository(async_session=session)


async def get_user_repo(session: DBSession) -> UserRepository:
    return UserRepository(async_session=session)


async def get_email_repo(session: DBSession) -> EmailRepository:
    return EmailRepository(async_session=session)


OtpRepo = Annotated[OtpRepository, Depends(get_otp_repo)]
UserRepo = Annotated[UserRepository, Depends(get_user_repo)]
EmailRepo = Annotated[EmailRepository, Depends(get_email_repo)]


#  -------------------- Service dependency ---------------------------- #


async def get_auth_service(otp_repo: OtpRepo, redis_repo: RedisRepo) -> AuthService:
    return AuthService(otp_repo=otp_repo, redis_repo=redis_repo)


async def get_auth_service(otp_repo: OtpRepo, redis_repo: RedisRepo) -> AuthService:
    return AuthService(otp_repo=otp_repo, redis_repo=redis_repo)


async def get_user_service(user_repo: UserRepo) -> UserService:
    return UserService(user_repo=user_repo)


async def get_email_service(email_repo: EmailRepo) -> EmailService:
    return EmailService(email_repo=email_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
