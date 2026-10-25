from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://berth:berth@localhost:5432/berth"
    jwt_secret: str = "dev-only-secret"
    cron_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "production" and settings.jwt_secret == "dev-only-secret":
        raise RuntimeError("JWT_SECRET must be set in production")
    return settings
