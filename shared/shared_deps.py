from typing import Annotated
from redis.asyncio import Redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


from shared.repo.redis import RedisRepository
from shared.repo.uow import UnitOfWorkRepository
from apps.user_service.app.api.models.user import User
from shared.database.shared_session import get_session
from apps.user_service.app.api.repo.user import UserRepository
from apps.user_service.app.api.services.user import UserService

# ------------------- DB dependency ------------------------------ #

DBSession = Annotated[AsyncSession, Depends(get_session)]


# ------------------- Redis dependency ------------------------------ #
async def get_redis_client(request: Request) -> Redis:
    redis_client: Redis = request.app.state.redis
    return redis_client


RedisDep = Annotated[Redis, Depends(get_redis_client)]


#  ------------------- Repo dependency ----------------------------- #


async def get_redis_repo(redis: RedisDep) -> RedisRepository:
    return RedisRepository(async_redis=redis)


async def get_unit_of_work(session: DBSession) -> UnitOfWorkRepository:
    return UnitOfWorkRepository(session=session)


RedisRepo = Annotated[RedisRepository, Depends(get_redis_repo)]
UnitOfWorkRepo = Annotated[UnitOfWorkRepository, Depends(get_unit_of_work)]


# -------------------- Current user dependency ---------------------- #


async def get_current_user(request: Request, session: DBSession) -> User:
    user_service = UserService(
        user_repo=UserRepository(async_session=session),
    )

    user_type: str = request.headers.get("X-USER-TYPE")
    user_email: str = request.headers.get("X-USER-EMAIL")

    if user_type == "email":
        curr_user: User = await user_service.get_user_by_email(
            email=user_email, is_verified=True
        )
    else:
        curr_user: User = await user_service.get_user_by_email(
            google_email=user_email, is_verified=True
        )

    return curr_user


CurrUserDep = Annotated[User, Depends(get_current_user)]
