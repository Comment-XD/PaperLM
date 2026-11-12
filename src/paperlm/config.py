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

    # Database (paper-quality metadata)
    database_url: str = "postgresql+psycopg://paperlm:paperlm@postgres:5432/paperlm"
    # Keep writing transformed/<id>.stats.json as a cheap debug artifact. The DB
    # is the queryable source of truth; set false to skip the extra S3 write.
    write_stats_json: bool = True

    # S3 storage
    s3_bucket: str
    s3_endpoint_url: str | None = None
    raw_prefix: str = "raw/"
    extracted_prefix: str = "extracted/"
    transformed_prefix: str = "transformed/"
    tokenized_prefix: str = "tokenized/"
    selections_prefix: str = "selections/"

    # GROBID
    grobid_url: str = "http://grobid:8070"
    grobid_timeout_seconds: int = Field(default=300, gt=0)

    # Tokenize stage
    tokenizer_name: str = "gpt2"
    tokenizer_backend: str = "tiktoken"  # "tiktoken" or "hf"
    tokenize_chunk_size: int = Field(default=64, gt=0)  # papers per task/shard
    local_tokenized_dir: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance (built from env on first call)."""
    return Settings()
