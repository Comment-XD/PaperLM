"""Celery tasks wrapping the extraction and transform pipeline stages."""

import requests
from botocore.exceptions import BotoCoreError
from sqlalchemy.exc import OperationalError

from paperlm.celery_app import app
from paperlm.pipeline import (
    process_paper_pdf,
    process_paper_tei,
    process_tokenize_shard,
)


@app.task(
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    max_retries=3,
)
def process_paper(pdf_key: str) -> str:
    """Extract one PDF (S3 key) to TEI XML; retries on transient GROBID/HTTP failures."""
    return process_paper_pdf(pdf_key)


@app.task(
    autoretry_for=(BotoCoreError, OperationalError),
    retry_backoff=True,
    max_retries=3,
)
def transform_paper(tei_key: str) -> dict:
    """Transform one TEI XML (S3 key) into clean text + a stats row.

    Chained after :func:`process_paper`, which returns the TEI key that Celery
    feeds in here as ``tei_key``. Retries only on transient S3 I/O and DB
    connection errors (``OperationalError``) -- XML parse errors and
    deterministic DB errors (bad data, schema) fail fast instead of looping.
    """
    return process_paper_tei(tei_key)


@app.task(
    autoretry_for=(BotoCoreError, OperationalError),
    retry_backoff=True,
    max_retries=3,
)
def tokenize_shard(run_id: str, shard_index: int, arxiv_ids: list[str]) -> dict:
    """Tokenize one chunk of papers into a uint16 shard under ``run_id``.

    Dispatched by :mod:`paperlm.tokenize_enqueue` from a selection manifest.
    Retries on transient S3/DB errors; the shard key is deterministic from
    ``run_id`` + ``shard_index`` so a retry overwrites rather than duplicates.
    """
    return process_tokenize_shard(run_id, shard_index, arxiv_ids)
