"""Tests for the pure extraction pipeline with storage/grobid stubbed out."""

from pathlib import Path

import pytest

from paperlm import grobid, pipeline, storage
from paperlm.config import get_settings


@pytest.fixture(autouse=True)
def _bucket_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "bucket")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_process_paper_pdf(monkeypatch):
    downloaded: dict[str, Path] = {}
    uploaded: dict[str, bytes] = {}
    tei = b"<TEI>xml</TEI>"

    def fake_download(key: str, destination: Path) -> None:
        downloaded["key"] = key
        destination.write_bytes(b"%PDF-1.7 fake")

    def fake_extract(pdf_path: Path) -> bytes:
        assert pdf_path.exists()
        return tei

    def fake_upload(key: str, data: bytes) -> None:
        uploaded[key] = data

    monkeypatch.setattr(storage, "download", fake_download)
    monkeypatch.setattr(grobid, "extract_tei", fake_extract)
    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    output_key = pipeline.process_paper_pdf("raw/papers/attention.pdf")

    assert output_key == "extracted/attention.tei.xml"
    assert downloaded["key"] == "raw/papers/attention.pdf"
    assert uploaded == {"extracted/attention.tei.xml": tei}
