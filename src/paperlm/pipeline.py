"""Pure extraction pipeline: download a PDF, run GROBID, store the TEI XML.

Deliberately free of Celery so it can be unit-tested without a broker.
"""

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from paperlm import grobid, storage, transform
from paperlm.config import get_settings


def process_paper_pdf(pdf_key: str) -> str:
    """Extract one PDF (by S3 key) to TEI XML and return the output key."""
    settings = get_settings()
    stem = Path(pdf_key).stem
    output_key = f"{settings.extracted_prefix}{stem}.tei.xml"

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / f"{stem}.pdf"
        storage.download(pdf_key, pdf_path)
        tei_xml = grobid.extract_tei(pdf_path)
        storage.upload_bytes(output_key, tei_xml)

    return output_key


def process_paper_tei(tei_key: str) -> dict:
    """Transform one TEI XML (by S3 key) into clean text + a stats row.

    Writes two objects under the transformed prefix -- ``<stem>.txt`` and
    ``<stem>.stats.json`` -- and returns the keys plus the stats row.
    """
    settings = get_settings()
    stem = Path(tei_key).stem
    if stem.endswith(".tei"):
        stem = stem[: -len(".tei")]

    text_key = f"{settings.transformed_prefix}{stem}.txt"
    stats_key = f"{settings.transformed_prefix}{stem}.stats.json"

    with tempfile.TemporaryDirectory() as tmpdir:
        tei_path = Path(tmpdir) / f"{stem}.tei.xml"
        storage.download(tei_key, tei_path)
        result = transform.transform(tei_path.read_bytes())

    storage.upload_bytes(text_key, result.text.encode("utf-8"))
    storage.upload_bytes(
        stats_key,
        json.dumps(asdict(result.stats), ensure_ascii=False, indent=2).encode(
            "utf-8"
        ),
    )

    return {
        "tei_key": tei_key,
        "text_key": text_key,
        "stats_key": stats_key,
        "stats": asdict(result.stats),
    }