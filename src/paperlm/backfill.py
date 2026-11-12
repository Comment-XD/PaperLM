"""Backfill paper_stats from the TEI XML already in S3.

Re-runs the transform stage (TEI -> clean text + stats row) for every
``extracted/<id>.tei.xml``, WITHOUT re-running GROBID. Use this once to populate
``paper_stats`` for papers processed before the database existed; it also
refreshes ``transformed/<id>.txt`` and ``<id>.stats.json``. Idempotent -- upserts
are keyed on ``arxiv_id``, so re-running is safe.

Run inside the stack so the workers (which can reach Postgres and Redis) do the
work::

    docker compose -f docker/docker-compose.yml run --rm celery python -m paperlm.backfill
"""

from paperlm.config import get_settings
from paperlm.storage import list_keys
from paperlm.tasks import transform_paper


def main() -> None:
    """Enqueue the transform task for every extracted TEI XML key."""
    settings = get_settings()
    count = 0
    for key in list_keys(settings.extracted_prefix):
        if key.endswith(".tei.xml"):
            transform_paper.delay(key)
            count += 1
    print(f"Enqueued transform for {count} extracted paper(s).")


if __name__ == "__main__":
    main()
