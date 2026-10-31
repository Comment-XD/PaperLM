"""Enqueue a Celery task for every raw PDF found in S3."""

from paperlm.config import get_settings
from paperlm.storage import list_keys
from paperlm.tasks import process_paper


def main() -> None:
    """Dispatch process_paper for each .pdf key under the raw prefix."""
    settings = get_settings()
    count = 0
    for key in list_keys(settings.raw_prefix):
        if key.endswith(".pdf"):
            process_paper.delay(key)
            count += 1
    print(f"Enqueued {count} paper(s).")


if __name__ == "__main__":
    main()
