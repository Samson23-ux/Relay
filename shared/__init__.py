from shared.worker.db import get_db_session
from shared.repo.redis import RedisRepository
from shared.worker.celery_app import celery_app
from shared.repo.uow import UnitOfWorkRepository
from shared.repo.base_repo import BaseRepository
from shared.worker.services import get_redis_repo
from shared.database.shared_session import get_session
from shared.worker.tasks.base import BaseTaskWithFailure
from shared.core.shared_config import get_global_settings
from shared.core.exception_handlers import GlobalExceptionHandler
from shared.shared_deps import get_redis_client, RedisRepo, DBSession, UnitOfWorkRepo
from shared.schemas.response import SuccessResponse, AllSuccessResponse, ErrorResponse
from shared.core.exceptions import (
    AppException,
    create_exception_handler,
    ServerError,
    ServiceUnavailable,
    MaxRetriesError,
)

__all__ = [
    "RedisRepo",
    "DBSession",
    "celery_app",
    "get_session",
    "ServerError",
    "AppException",
    "ErrorResponse",
    "get_db_session",
    "BaseRepository",
    "get_redis_repo",
    "UnitOfWorkRepo",
    "RedisRepository",
    "MaxRetriesError",
    "SuccessResponse",
    "get_redis_client",
    "AllSuccessResponse",
    "ServiceUnavailable",
    "BaseTaskWithFailure",
    "get_global_settings",
    "UnitOfWorkRepository",
    "GlobalExceptionHandler",
    "create_exception_handler",
]
