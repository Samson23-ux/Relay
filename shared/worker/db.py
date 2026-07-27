from typing import Any
from redis import Redis
from redis.retry import Retry
from collections.abc import Generator
from redis.connection import ConnectionPool
from sqlalchemy import Engine, create_engine
from redis.backoff import ExponentialBackoff
from sqlalchemy.orm import Session, sessionmaker
from redis.exceptions import TimeoutError, ConnectionError

from shared.core.shared_config import get_global_settings


SETTINGS = get_global_settings()

db_engine: Engine = create_engine(
    url=SETTINGS.SYNC_DB_URL,
    pool_size=10,
    pool_timeout=10.0,
    pool_pre_ping=True,
    max_overflow=5,
    connect_args={"options": "-c timezone=utc"},
)

db_session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

redis_pool = ConnectionPool.from_url(
    SETTINGS.REDIS_URL,
    decode_responses=True,
    max_connections=50,
    retry=Retry(ExponentialBackoff(cap=1.0, base=0.1), retries=5),
    retry_on_error=(TimeoutError, ConnectionError),
    retry_on_timeout=True,
)


def get_db_session() -> Generator[Session, Any, None]:
    with db_session() as session:
        yield session


def get_redis_client() -> Generator[Redis, Any, None]:
    with Redis(connection_pool=redis_pool) as redis:
        yield redis
