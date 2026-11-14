import os

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    DATABASE_ECHO_DEBUG_LOG: bool = False
    APP_ENV: str = os.getenv("APP_ENV", "local")
    CORS_ORIGINS: list[str] = []
    VERSION: str = "0.0.1"
    URL_PREFIX: str = '/api/v1'
    PORT: int = 8080
    RELOAD: bool = False
    WORKERS: int = 4

    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str | None = None
    REDIS_SESSION_PREFIX: str = "session:"
    REDIS_USER_SESSION_PREFIX: str = "user_sessions:"
    REDIS_OTP_PREFIX: str = "otp:"

    REDIS_RATE_LIMIT_PREFIX: str = "rate_limit"
    RATE_LIMIT_RESET_TIME: int = 300

    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE: str = "session_id"
    SESSION_TTL: int = 86400

    CLIENT_SESSION_COOKIE: str = "client_session_id"
    REDIS_CLIENT_SESSION_PREFIX: str = "client_session:"
    REDIS_CLIENT_USER_SESSION_PREFIX: str = "client_user_sessions:"
    REDIS_CLIENT_OTP_PREFIX: str = "client_otp:"
    REDIS_CLIENT_AUTH_LINK_PREFIX: str = "client_auth_link:"
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_BOT_USERNAME: str = "muzeon_auth_bot"

    OTP_TTL: int = 300
    OTP_COOLDOWN_PREFIX: str = "otp_cooldown:"
    OTP_COOLDOWN: int = 180

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: EmailStr = "noreply@muzeon.ru"
    USE_TLS: bool = True



class DevSettings(Settings):
    pass


class LocalSettings(Settings):
    DATABASE_ECHO_DEBUG_LOG: bool = False # Change to True
    SESSION_COOKIE_SECURE: bool = False
    RELOAD: bool = True
    WORKERS: int = 1



settings_by_name = {
    "dev": DevSettings,
    "local": LocalSettings,
}

settings = settings_by_name[os.getenv("APP_ENV") or "local"]()
