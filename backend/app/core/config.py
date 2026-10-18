"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = True

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://haron:haron_secret@localhost:5436/haron"
    )
    REDIS_URL: str = Field(default="redis://localhost:6382/0")

    JWT_SECRET_KEY: str = Field(
        default="development_jwt_secret_key_change_in_production_32chars_min"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "haron-assets"
    S3_REGION: str = "us-east-1"

    PROMETHEUS_METRICS_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
