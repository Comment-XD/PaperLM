"""Pure extraction pipeline: download a PDF, run GROBID, store the TEI XML.

Deliberately free of Celery so it can be unit-tested without a broker.
"""

import tempfile
from pathlib import Path

from paperlm import grobid, storage
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
