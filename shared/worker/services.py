from shared.repo.redis import RedisRepository
from shared.shared_deps import get_redis_client


def get_redis_repo() -> RedisRepository:
    return RedisRepository(sync_redis=get_redis_client())
