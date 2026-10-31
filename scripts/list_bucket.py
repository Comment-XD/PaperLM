"""List the contents of the S3 bucket (key, size, last modified)."""

import sys

import boto3

from paperlm.config import get_settings


def _human(size: int) -> str:
    """Render a byte count in a short human-readable form."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def main() -> None:
    """Print every object in the bucket, optionally filtered by a prefix arg."""
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    settings = get_settings()
    client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url)

    paginator = client.get_paginator("list_objects_v2")
    count = 0
    total = 0
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            count += 1
            total += obj["Size"]
            modified = obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"{modified}  {_human(obj['Size']):>8}  {obj['Key']}")

    scope = f" under {prefix!r}" if prefix else ""
    print(f"\n{count} object(s){scope}, {_human(total)} total in {settings.s3_bucket}")


if __name__ == "__main__":
    main()
