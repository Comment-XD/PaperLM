"""Application settings, loaded once from the environment via get_settings()."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the PaperLM extraction pipeline."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Broker / Celery
    redis_url: str = "redis://redis:6379/0"
    visibility_timeout_seconds: int = Field(default=3600, gt=0)

    # S3 storage
    s3_bucket: str
    s3_endpoint_url: str | None = None
    raw_prefix: str = "raw/papers/"
    extracted_prefix: str = "extracted/"
    transformed_prefix: str = "transformed/"

    # GROBID
    grobid_url: str = "http://grobid:8070"
    grobid_timeout_seconds: int = Field(default=300, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance (built from env on first call)."""
    return Settings()
