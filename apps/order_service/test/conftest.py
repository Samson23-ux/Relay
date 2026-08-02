import pytest_asyncio
from sqlalchemy import text
from uuid import uuid7, UUID
from redis.asyncio import Redis
from unittest.mock import patch
from sqlalchemy.pool import NullPool
from asgi_lifespan import LifespanManager
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
from apps.user_service.app.api.models.user import User
from shared.database.shared_session import get_session
from shared.core.shared_config import get_global_settings
from apps.order_service.app.api import models  # noqa: F401
from apps.product_service.app.api.models.product import Product  # noqa: F401
from shared.shared_deps import get_redis_client, request_metadata, get_current_user


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    async_db_engine: AsyncEngine = create_async_engine(
        url=get_global_settings().ASYNC_TEST_DB_URL, poolclass=NullPool
    )

    user_stmt = """
        INSERT INTO users (
        id,
        type,
        role,
        email,
        hashed_password,
        is_active,
        is_verified,
        created_at
        )
        VALUES
        (
            '019fbd28-ea23-76ef-b14a-64a857bc11f3',
            'email',
            'user',
            'user@example.com',
            'test_user_password',
            'true',
            'true',
            NOW()
        );
    """

    prd_1_stmt = """
        INSERT INTO products (
        id,
        name,
        description,
        serial,
        price,
        quantity,
        created_at
        )
        VALUES
        (
            '019fb2f7-2003-74d1-91fb-79bcb506c77f',
            'test_product',
            'This is a fake test product.',
            'EumHUV41owYwmnzpjVKYng',
            '50.00',
            '50',
            NOW()
        );
    """

    prd_2_stmt = """
        INSERT INTO products (
        id,
        name,
        description,
        serial,
        price,
        quantity,
        created_at
        )
        VALUES
        (
            '019fbd53-b8da-75fc-904e-b1d70c2e2c6e',
            'test_product_1',
            'This is a fake test product.',
            'L9ZWvaU24w42iqYNQKv1Vw',
            '50.00',
            '50',
            NOW()
        );
    """

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
        await conn.execute(text(user_stmt))
        await conn.execute(text(prd_1_stmt))
        await conn.execute(text(prd_2_stmt))

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


@pytest_asyncio.fixture
async def async_client(async_session: AsyncSession, test_redis_client: Redis):
    async def get_test_session():
        return async_session

    fake_user = User(
        id=UUID("019fbd28-ea23-76ef-b14a-64a857bc11f3"),
        type="email",
        role="admin",
        email="user@example.com",
        hashed_password="test_user_password",
    )

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_redis_client] = lambda: test_redis_client
    app.dependency_overrides[request_metadata] = lambda: {"upstream_instance": "test"}

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://localhost/api/v1"
        ) as client:
            yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def mock_log_task():
    with (
        patch("shared.utils.save_log.apply_async") as create_log_mock,
        patch("shared.utils.update_log.apply_async") as update_log_mock,
    ):
        yield

    # create_log_mock.assert_called()
    # update_log_mock.assert_called()


@pytest_asyncio.fixture
async def create_cart(async_client: AsyncClient) -> Response:
    cart_item: dict = {
        "product_id": "019fb2f7-2003-74d1-91fb-79bcb506c77f",
        "quantity": 2,
    }
    res: Response = await async_client.post("/carts", json=cart_item)
    return res
