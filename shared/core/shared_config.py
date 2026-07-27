from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class GlobalSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_encoding="utf-8",
        extra="allow",
        case_sensitive=False,
    )

    # environment
    ENVIRONMENT: str = "development"

    # api details
    API_PREFIX: str = "/api/v1"
    API_TITLE: str = "Cowrite"
    API_VERSION: str = "v1.0"
    API_DESCRIPTION: str = "A Minimalistic API Gateway"

    # async db
    ASYNC_DB_URL: str

    # test db
    ASYNC_TEST_DB_URL: str

    # sync db
    SYNC_DB_URL: str

    # redis
    REDIS_URL: str

    # sentry
    SENTRY_SDK_DSN: str

    # rabbitmq
    BROKER_URL: str

    # idempotency
    IDEMPOTENCY_KEY_TTL: int = 60 * 60 * 24

    # resend email
    API_EMAIL: str
    RESEND_API_KEY: str


@lru_cache(maxsize=1)
def get_global_settings():
    return GlobalSettings()
