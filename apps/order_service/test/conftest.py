import pytest_asyncio
from uuid import uuid7
from sqlalchemy import text
from redis.asyncio import Redis
from sqlalchemy.pool import NullPool
from datetime import datetime, timezone
from asgi_lifespan import LifespanManager
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport, Response
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection,
    AsyncTransaction,
)


from shared.models.base import Base
from apps.order_service.app.main import app
from shared.services.request import Request
from apps.user_service.app.api.models.user import User
from shared.database.shared_session import get_session
from shared.core.shared_config import get_global_settings
from apps.order_service.app.api import models  # noqa: F401
from apps.order_service.app.deps import get_request_service
from apps.product_service.app.api.schemas.product import ProductResponse
from shared.shared_deps import get_redis_client, request_metadata, get_current_user


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    async_db_engine: AsyncEngine = create_async_engine(
        url=get_global_settings().ASYNC_TEST_DB_URL, poolclass=NullPool
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
            get_global_settings().REDIS_URL, decode_responses=True
        )
        yield redis_client
    finally:
        await redis_client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def flush_redis(test_redis_client: Redis):
    yield
    await test_redis_client.flushdb()


def get_product_1() -> tuple[ProductResponse]:
    prd_1: ProductResponse = ProductResponse(
        id=uuid7(),
        name="test_product",
        description="This is a fake test product.",
        serial="EumHUV41owYwmnzpjVKYng",
        price="50.00",
        quantity="15",
        created_at=datetime.now(timezone.utc),
        updated_at=None
    )

    prd_2: ProductResponse = ProductResponse(
        id=uuid7(),
        name="test_product_1",
        description="This is a fake test product.",
        serial="aJPqCYM00MaZ6kCy2ytQ",
        price="80.00",
        quantity="10",
        created_at=datetime.now(timezone.utc),
        updated_at=None
    )

    return prd_1, prd_2


async def mock_request_service() -> MagicMock:
    response = AsyncMock()
    request = MagicMock(spec=Request)

    prd_1, prd_2 = get_product_1()

    response.json.side_effects = [{"data": prd_1}, {"data": prd_2}]
    request.get.return_value = response

    return request


@pytest_asyncio.fixture
async def async_client(async_session: AsyncSession, test_redis_client: Redis):
    async def get_test_session():
        return async_session

    fake_user = User(
        id=uuid7(),
        type="email",
        role="admin",
        email="user@example.com",
        hashed_password="test_user_password",
    )

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_request_service] = mock_request_service
    app.dependency_overrides[get_redis_client] = lambda: test_redis_client
    app.dependency_overrides[request_metadata] = lambda: {"upstream": "test"}

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://localhost/api/v1"
        ) as client:
            yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def mock_log_task():
    with patch("shared.utils.save_log.apply_async"):
        yield


@pytest_asyncio.fixture
async def create_cart(async_client: AsyncClient) -> Response:
    cart_item: dict = {"product_id": uuid7(), "quantity": 2}
    res: Response = await async_client.post("/carts", json=cart_item)
    return res
