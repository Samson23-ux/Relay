from shared import RedisRepository, get_redis_client


def get_redis_repo() -> RedisRepository:
    return RedisRepository(sync_redis=get_redis_client())
