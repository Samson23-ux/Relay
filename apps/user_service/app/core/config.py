from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class UserSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_encoding="utf-8", extra="allow", case_sensitive=False,
    )

    # Argon2
    ARGON2_PASSWORD_PEPPER: str

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_TIME: int = 15
    REFRESH_TOKEN_EXPIRE_TIME: int = 1
    ACCESS_TOKEN_SECRET_KEY: str
    REFRESH_TOKEN_SECRET_KEY: str

    # google oauth
    GOOGLE_CLIENT_ID: str
    GOOGLE_OAUTH_URL: str = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_CALLBACK_URL: str = "http://localhost:8000/api/v1/auth/google/callback"

    # session middleware
    SESSION_SECRET_KEY: str

    # otp
    OTP_EXPIRE_TIME: int = 15


@lru_cache(maxsize=1)
def get_user_settings():
    return UserSettings()
