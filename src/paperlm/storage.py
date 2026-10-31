"""S3 access: a cached boto3 client plus download/upload/list helpers."""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import boto3

from paperlm.config import get_settings


@lru_cache
def get_client():
    """Return a cached boto3 S3 client honouring the configured endpoint URL."""
    settings = get_settings()
    return boto3.client("s3", endpoint_url=settings.s3_endpoint_url)


def download(key: str, destination: Path) -> None:
    """Download the object at ``key`` into the local ``destination`` path."""
    settings = get_settings()
    get_client().download_file(settings.s3_bucket, key, str(destination))


def upload_bytes(key: str, data: bytes) -> None:
    """Upload raw ``data`` to the object at ``key``."""
    settings = get_settings()
    get_client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data)


def list_keys(prefix: str) -> Iterator[str]:
    """Yield every object key under ``prefix``, paging through all results."""
    settings = get_settings()
    paginator = get_client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield obj["Key"]
