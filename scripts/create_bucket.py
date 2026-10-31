"""Idempotently create the S3 bucket (LocalStack has no persistence)."""

import boto3
from botocore.exceptions import ClientError

from paperlm.config import get_settings


def main() -> None:
    """Create the configured bucket if it does not already exist."""
    settings = get_settings()
    client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url)
    region = client.meta.region_name

    try:
        client.head_bucket(Bucket=settings.s3_bucket)
        print(f"Bucket already exists: {settings.s3_bucket}")
        return
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status != 404:
            raise

    if region and region != "us-east-1":
        client.create_bucket(
            Bucket=settings.s3_bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    else:
        client.create_bucket(Bucket=settings.s3_bucket)
    print(f"Created bucket: {settings.s3_bucket}")


if __name__ == "__main__":
    main()
