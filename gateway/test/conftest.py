import respx
from jose import jwt
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import text
from redis.asyncio import Redis
from sqlalchemy.pool import NullPool
from asgi_lifespan import LifespanManager
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport, Response
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection,
    AsyncTransaction,
)


from gateway.app.main import app
from shared.models.base import Base
from shared.database.shared_session import get_session
from shared.core.shared_config import get_global_settings
from apps.user_service.app.api import models  # noqa: F401
from shared.services.request import Request as CustomRequest
from apps.user_service.app.core.config import get_user_settings
from shared.shared_deps import get_redis_client, request_metadata

USER_SETTINGS = get_user_settings()
GLOBAL_SETTINGS = get_global_settings()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    async_db_engine: AsyncEngine = create_async_engine(
        url=GLOBAL_SETTINGS.ASYNC_TEST_DB_URL, poolclass=NullPool
    )

    async with async_db_engine.begin() as conn:
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION uuid_generate_v7()
                RETURNS UUID
                LANGUAGE SQL
                VOLATILE
                AS $$
                    SELECT encode(
                        set_bit(
                            set_bit(
                                overlay(
                                    uuid_send(gen_random_uuid())
                                    placing substring(int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint) FROM 3)
                                    FROM 1 FOR 6
                                ),
                                52, 1
                            ),
                            53, 1
                        ),
                        'hex'
                    )::uuid
                $$;
        """))
        await conn.run_sync(Base.metadata.create_all)

    yield async_db_engine

    async with async_db_engine.begin() as conn:
        await conn.execute(text("DROP FUNCTION IF EXISTS uuid_generate_v7 CASCADE"))
        await conn.execute(text("DROP EXTENSION IF EXISTS pgcrypto CASCADE"))
        await conn.run_sync(Base.metadata.drop_all)

    await async_db_engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine: AsyncEngine):
    async_connection: AsyncConnection = await async_engine.connect()
    async_transaction: AsyncTransaction = await async_connection.begin()

    session = async_sessionmaker(
        bind=async_connection,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async_session: AsyncSession = session()
    yield async_session

    await async_session.close()
    await async_transaction.rollback()
    await async_connection.close()


@pytest_asyncio.fixture
async def test_redis_client():
    try:
        redis_client: Redis = Redis.from_url(
            GLOBAL_SETTINGS.REDIS_URL, decode_responses=True
        )
        yield redis_client
    finally:
        await redis_client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def flush_redis(test_redis_client: Redis):
    yield
    await test_redis_client.flushdb()


@pytest_asyncio.fixture
async def async_client(async_session: AsyncSession, test_redis_client: Redis):
    async def get_test_session():
        return async_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_redis_client] = lambda: test_redis_client
    app.dependency_overrides[request_metadata] = lambda: {"upstream_instance": "test"}

    with respx.mock:
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app), base_url="http://localhost/api/v1"
            ) as client:
                yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def mock_request_class():
    path: str = "gateway.app.middlewares.proxy.CustomRequest"

    request = MagicMock(spec=CustomRequest)

    with patch(path) as request_mock:
        request_mock.return_value = request
        yield request


def get_access_token():
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=USER_SETTINGS.ACCESS_TOKEN_EXPIRE_TIME
    )

    payload: dict = {
        "sub": "user@example.com",
        "exp": exp,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid4()),
        "userrole": "user",
        "usertype": "email",
    }

    token: str = jwt.encode(
        claims=payload,
        key=USER_SETTINGS.ACCESS_TOKEN_SECRET_KEY,
        algorithm=USER_SETTINGS.JWT_ALGORITHM,
    )

    return token


@pytest_asyncio.fixture(loop_scope="session")
async def login(async_client: AsyncClient, mock_request_class):
    login_payload: dict = {
        "email": "user@example.com",
        "password": "test_user_password",
    }

    mock_request_class.post.return_value = Response(
        status_code=201,
        json={
            "message": "Login completed successfully",
            "data": {
                "access_token": get_access_token(),
                "token_type": "bearer",
            },
        },
    )

    res: Response = await async_client.post(
        "/auth/login",
        json=login_payload,
    )

    json_res = res.json()

    assert res.status_code == 201
    assert json_res["message"] == "Login completed successfully"
    assert "access_token" in json_res["data"]

    mock_request_class.post.assert_called_once

    return res


@pytest_asyncio.fixture(autouse=True)
async def mock_log_task():
    with patch("shared.utils.save_log.apply_async"):
        yield
