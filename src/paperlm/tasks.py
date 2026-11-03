"""Celery task wrapping the extraction pipeline with retry rules."""

import requests

from paperlm.celery_app import app
from paperlm.pipeline import process_paper_pdf, process_paper_tei


@app.task(
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    max_retries=3,
)
def process_paper(pdf_key: str) -> str:
    """Process one PDF S3 key; retries on transient GROBID/HTTP failures."""
    return process_paper_pdf(pdf_key)
