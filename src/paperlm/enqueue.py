"""Enqueue the extract -> transform chain for every raw PDF found in S3."""

from celery import chain

from paperlm.config import get_settings
from paperlm.storage import list_keys
from paperlm.tasks import process_paper, transform_paper


def main() -> None:
    """Dispatch the extract->transform chain for each .pdf key under the raw prefix.

    Each paper runs ``process_paper`` (PDF -> TEI XML) then ``transform_paper``
    (TEI XML -> text + stats); Celery passes the extraction task's returned TEI
    key straight into the transform task.
    """
    settings = get_settings()
    count = 0
    for key in list_keys(settings.raw_prefix):
        if key.endswith(".pdf"):
            chain(process_paper.s(key), transform_paper.s()).apply_async()
            count += 1
    print(f"Enqueued {count} paper(s).")


if __name__ == "__main__":
    main()
