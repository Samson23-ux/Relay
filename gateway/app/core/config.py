from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class RelaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_encoding="utf-8",
        extra="allow",
        case_sensitive=False,
    )

    UPSTREAMS: list = ["user_service", "order_service", "product_service"]

    HOP_BY_HOP_HEADERS: set = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "content-length",
    }


@lru_cache(maxsize=1)
def get_relay_settings():
    return RelaySettings()
