"""Tests for the pure extraction pipeline with storage/grobid stubbed out."""

from pathlib import Path

import pytest

from paperlm import db, grobid, pipeline, storage, transform
from paperlm.config import get_settings
from paperlm.models import Stats, TransformResult


@pytest.fixture(autouse=True)
def _bucket_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "bucket")
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
    yield
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()


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


def _fake_result() -> TransformResult:
    return TransformResult(
        title="A Paper",
        abstract="An abstract.",
        text="Body text.",
        stats=Stats(
            word_count=2,
            char_count=10,
            alpha_ratio=0.9,
            section_count=1,
            repeated_line_fraction=0.0,
            dropped_headings=["references"],
            missing_title=False,
            missing_abstract=False,
        ),
    )


def test_process_paper_tei(monkeypatch):
    uploaded: dict[str, bytes] = {}
    upserted: dict = {}
    result = _fake_result()

    monkeypatch.setattr(
        storage, "download", lambda key, dest: Path(dest).write_bytes(b"<TEI/>")
    )
    monkeypatch.setattr(transform, "transform", lambda data: result)
    monkeypatch.setattr(
        storage, "upload_bytes", lambda key, data: uploaded.__setitem__(key, data)
    )
    monkeypatch.setattr(db, "upsert_paper_stats", lambda row: upserted.update(row))

    out = pipeline.process_paper_tei("extracted/2606.15253.tei.xml")

    # Text + stats.json written to S3 under the transformed prefix.
    assert out["text_key"] == "transformed/2606.15253.txt"
    assert out["stats_key"] == "transformed/2606.15253.stats.json"
    assert uploaded["transformed/2606.15253.txt"] == b"Body text."
    assert "transformed/2606.15253.stats.json" in uploaded

    # The DB row is upserted with the mapped stats + artifact pointers.
    assert upserted["arxiv_id"] == "2606.15253"
    assert upserted["word_count"] == 2
    assert upserted["text_key"] == "transformed/2606.15253.txt"


def test_process_paper_tei_skips_stats_json_when_disabled(monkeypatch):
    monkeypatch.setenv("WRITE_STATS_JSON", "false")
    get_settings.cache_clear()

    uploaded: dict[str, bytes] = {}
    monkeypatch.setattr(
        storage, "download", lambda key, dest: Path(dest).write_bytes(b"<TEI/>")
    )
    monkeypatch.setattr(transform, "transform", lambda data: _fake_result())
    monkeypatch.setattr(
        storage, "upload_bytes", lambda key, data: uploaded.__setitem__(key, data)
    )
    monkeypatch.setattr(db, "upsert_paper_stats", lambda row: None)

    out = pipeline.process_paper_tei("extracted/2606.15253.tei.xml")

    assert out["stats_key"] is None
    assert list(uploaded) == ["transformed/2606.15253.txt"]
