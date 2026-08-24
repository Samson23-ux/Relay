import json
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


# --------------------- Request metadata ---------------------------- #


async def request_metadata(request: Request) -> dict:
    return {
        "trace_id": request.headers.get("x-trace-id"),
        "span_id": request.state.span_id,  # set by a middleware layer
        "parent_span_id": request.state.parent_span_id,  # set by a middleware layer
        "client_ip": request.client.host,
        "upstream": request.headers.get("x-upstream"),
        "upstream_instance": request.headers.get("x-upstream-instance"),
        "upstream_url": str(request.url),
        "method": request.method,
        "path": request.url.path,
    }


RequestMetaData = Annotated[dict, Depends(request_metadata)]


# -------------------- Current user dependency ---------------------- #


async def get_current_user(
    request: Request,
    redis: RedisRepo,
    session: DBSession,
    request_meta: RequestMetaData,
) -> User:
    circuit_key: str = f"circuit:{request_meta.get("upstream")}"
    user_service = UserService(
        redis_repo=redis,
        user_repo=UserRepository(async_session=session),
    )

    user_type: str = request.headers.get("x-user-type")
    user_email: str = request.headers.get("x-user-email")

    route_roles_header: str | None = request.headers.get("x-route-roles")
    route_roles: list[str] | None = (
        json.loads(route_roles_header) if route_roles_header else None
    )

    filters: dict = {"email": user_email, "is_verified": True}
    if route_roles:
        filters["role"] = route_roles

    if user_type == "email":
        curr_user: User = await user_service.get_user_by_email(
            circuit_key, request_meta, **filters
        )
    else:
        curr_user: User = await user_service.get_user_by_email(
            circuit_key, request_meta, **filters
        )

    return curr_user


CurrUserDep = Annotated[User, Depends(get_current_user)]
