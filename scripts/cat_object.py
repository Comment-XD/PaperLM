"""Print the contents of one S3 object (e.g. a TEI XML file) to stdout."""

import sys
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import boto3

from paperlm.config import get_settings


def main() -> None:
    """Fetch the object at the given key; pretty-print XML unless --raw."""
    args = [a for a in sys.argv[1:] if a != "--raw"]
    raw = "--raw" in sys.argv[1:]
    if len(args) != 1:
        sys.exit("usage: python -m scripts.cat_object [--raw] <key>")

    key = args[0]
    settings = get_settings()
    client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url)

    body = client.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
    text = body.decode("utf-8", errors="replace")

    if not raw and key.endswith((".xml", ".tei.xml")):
        try:
            text = minidom.parseString(body).toprettyxml(indent="  ").strip()
        except ExpatError:
            pass  # not well-formed; fall back to the raw text

    print(text)


if __name__ == "__main__":
    main()
