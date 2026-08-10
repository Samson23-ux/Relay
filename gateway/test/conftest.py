import respx
import secrets
from jose import jwt
import pytest_asyncio
from sqlalchemy import text
from uuid import uuid7, uuid4
from redis.asyncio import Redis
from sqlalchemy.pool import NullPool
from asgi_lifespan import LifespanManager
from unittest.mock import patch, AsyncMock
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
from shared.repo.redis import RedisRepository
from apps.user_service.app.api.models.otp import Otp
from shared.database.shared_session import get_session
from apps.user_service.app.deps import get_auth_service
from shared.core.shared_config import get_global_settings
from apps.user_service.app.api import models  # noqa: F401
from apps.user_service.app.api.services.auth import AuthService
from shared.shared_deps import get_redis_client, request_metadata

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


# @pytest_asyncio.fixture
# async def create_user(async_client: AsyncClient):
#     sign_up_payload: dict = {
#         "email": "user@example.com",
#         "password": "test_user_password",
#     }

#     route = respx.post("http://user-service@:8001/api/v1/auth/signup").mock(
#         return_value=Response(
#             status_code=201,
#             json={
#                 "message": (
#                     "Sign up completed successfully."
#                     "Check your email for verification code and instructions"
#                 )
#             },
#         )
#     )

#     res: Response = await async_client.post(
#         "/auth/signup",
#         json=sign_up_payload,
#     )

#     req = route.calls[0].request

#     assert route.called
#     assert "x-trace-id" in req.headers
#     assert req.headers["x-upstream"] == "user_service"

#     return res


# def mock_auth_service(fake_otp: Otp, redis: Redis):
#     otp_repo = AsyncMock()
#     redis = RedisRepository(async_redis=redis)

#     otp_repo.get_record = AsyncMock(return_value=fake_otp)
#     auth_service = AuthService(otp_repo=otp_repo, redis_repo=redis)

#     app.dependency_overrides[get_auth_service] = lambda: auth_service


# @pytest_asyncio.fixture
# async def verify_user(
#     async_client: AsyncClient, create_user: Response, test_redis_client: Redis
# ):
#     otp_payload: dict = {
#         "email": "user@example.com",
#         "otp_code": "test_otp_token",
#     }

#     route = respx.patch("http://user-service@:8001/api/v1/auth/verify").mock(
#         return_value=Response(
#             status_code=200,
#             json={"message": "User email verified successfully"},
#         )
#     )

#     res: Response = await async_client.patch(
#         "/auth/verify",
#         json=otp_payload,
#     )

#     req = route.calls[0].request

#     assert route.called
#     assert "x-trace-id" in req.headers
#     assert req.headers["x-upstream"] == "user_service"

#     return res


def get_access_token():
    expire = (
        datetime.now(timezone.utc)
        + timedelta(days=GLOBAL_SETTINGS.REFRESH_TOKEN_EXPIRE_TIME),
    )

    payload: dict = {
        "sub": "user@example.com",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid4()),
        "userrole": "user",
        "usertype": "email",
    }

    token: str = jwt.encode(
        claims=payload,
        key=GLOBAL_SETTINGS.ACCESS_TOKEN_SECRET_KEY,
        algorithm=GLOBAL_SETTINGS.JWT_ALGORITHM,
    )

    return token


@pytest_asyncio.fixture
async def login(async_client: AsyncClient):
    login_payload: dict = {
        "email": "user@example.com",
        "password": "test_user_password",
    }

    route = respx.post("http://user-service@:8001/api/v1/auth/login").mock(
        return_value=Response(
            status_code=201,
            json={
                "message": "Login completed successfully",
                "data": {
                    "access_token": get_access_token(),
                    "token_type": "bearer",
                },
            },
        )
    )

    res: Response = await async_client.post(
        "/auth/login",
        json=login_payload,
    )

    req = route.calls[0].request

    assert route.called
    assert "x-trace-id" in req.headers
    assert req.headers["x-upstream"] == "user_service"

    return res


@pytest_asyncio.fixture(autouse=True)
async def mock_log_task():
    with patch("shared.utils.save_log.apply_async"):
        yield
