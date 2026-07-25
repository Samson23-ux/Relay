from typing import Annotated
from redis.asyncio import Redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


from shared import get_session, RedisRepository


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


RedisRepo = Annotated[RedisRepository, Depends(get_redis_repo)]
