from shared.repo.redis import RedisRepository
from shared.worker.db import get_db_session, get_redis_client


def get_redis_repo() -> RedisRepository:
    redis = next(get_redis_client())
    return RedisRepository(sync_redis=redis)


def get_log_service():
    from shared.repo.log import LogRepository
    from shared.services.log import LogService

    session = next(get_db_session())
    return LogService(log_repo=LogRepository(sync_session=session))
