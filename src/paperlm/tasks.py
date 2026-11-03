"""Celery tasks wrapping the extraction and transform pipeline stages."""

import requests
from botocore.exceptions import BotoCoreError

from paperlm.celery_app import app
from paperlm.pipeline import process_paper_pdf, process_paper_tei


@app.task(
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    max_retries=3,
)
def process_paper(pdf_key: str) -> str:
    """Extract one PDF (S3 key) to TEI XML; retries on transient GROBID/HTTP failures."""
    return process_paper_pdf(pdf_key)


@app.task(
    autoretry_for=(BotoCoreError,),
    retry_backoff=True,
    max_retries=3,
)
def transform_paper(tei_key: str) -> dict:
    """Transform one TEI XML (S3 key) into clean text + a stats row.

    Chained after :func:`process_paper`, which returns the TEI key that Celery
    feeds in here as ``tei_key``. Retries only on transient S3 I/O -- XML parse
    errors are deterministic, so they fail fast instead of looping.
    """
    return process_paper_tei(tei_key)
