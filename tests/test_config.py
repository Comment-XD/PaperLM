"""Tests for Settings loading, defaults, overrides and validation."""

import pytest
from pydantic import ValidationError

from paperlm.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the get_settings cache around every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_missing_bucket_raises(monkeypatch):
    monkeypatch.delenv("S3_BUCKET", raising=False)
    # _env_file=None stops pydantic from reading a developer's local .env.
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_defaults_apply(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "bucket")
    settings = Settings(_env_file=None)
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.visibility_timeout_seconds == 3600
    assert settings.s3_endpoint_url is None
    assert settings.raw_prefix == "raw/"
    assert settings.extracted_prefix == "extracted/"
    assert settings.grobid_url == "http://grobid:8070"
    assert settings.grobid_timeout_seconds == 300


def test_env_overrides_and_coerces_int(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "bucket")
    monkeypatch.setenv("GROBID_TIMEOUT_SECONDS", "200")
    settings = Settings(_env_file=None)
    assert settings.grobid_timeout_seconds == 200
    assert isinstance(settings.grobid_timeout_seconds, int)


def test_zero_timeout_rejected(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "bucket")
    monkeypatch.setenv("VISIBILITY_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
