from fastapi import Depends
from typing import Annotated


from shared import RedisRepo, DBSession
from apps.user_service import AuthService, OtpRepository, Security


# ------------------- Security dependency ------------------------------ #
async def get_security() -> Security:
    return Security()


SecurityDep = Annotated[Security, Depends(get_security)]


#  ------------------- Repo dependency ----------------------------- #

async def get_otp_repo(session: DBSession) -> OtpRepository:
    return OtpRepository(async_session=session)


OtpRepo = Annotated[OtpRepository, Depends(get_otp_repo)]


#  -------------------- Service dependency ---------------------------- #

async def get_auth_service(otp_repo: OtpRepo, redis_repo: RedisRepo) -> AuthService:
    return AuthService(otp_repo=otp_repo, redis_repo=redis_repo)
