from fastapi import Depends
from typing import Annotated


from shared.shared_deps import RedisRepo, DBSession
from apps.user_service.app.core.security import Security
from apps.user_service.app.api.repo.otp import OtpRepository
from apps.user_service.app.api.repo.user import UserRepository
from apps.user_service.app.api.services.auth import AuthService
from apps.user_service.app.api.services.user import UserService
from apps.user_service.app.api.repo.email import EmailRepository
from apps.user_service.app.api.services.email import EmailService


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


async def get_user_service(user_repo: UserRepo, redis: RedisRepo) -> UserService:
    return UserService(user_repo=user_repo, redis_repo=redis)


async def get_email_service(email_repo: EmailRepo, redis_repo: RedisRepo) -> EmailService:
    return EmailService(email_repo=email_repo, redis_repo=redis_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
