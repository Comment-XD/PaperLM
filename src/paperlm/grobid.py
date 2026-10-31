"""GROBID client: turn a local PDF into TEI XML."""

from pathlib import Path

import requests

from paperlm.config import get_settings


def extract_tei(pdf_path: Path) -> bytes:
    """POST ``pdf_path`` to GROBID and return the TEI XML response bytes."""
    settings = get_settings()
    url = f"{settings.grobid_url}/api/processFulltextDocument"
    with pdf_path.open("rb") as fh:
        response = requests.post(
            url,
            files={"input": fh},
            timeout=settings.grobid_timeout_seconds,
        )
    response.raise_for_status()
    return response.content
