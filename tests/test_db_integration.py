"""Integration tests for the real Postgres upsert path.

Requires a live database at ``DATABASE_URL`` (the compose ``postgres`` service).
Run with: ``uv run pytest -m integration`` (excluded from the default suite).
"""

import os

import pytest

from paperlm import db
from paperlm.config import get_settings
from paperlm.db_models import PaperStats

pytestmark = pytest.mark.integration


@pytest.fixture
def _clean_db():
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; skipping DB integration test")
    db.init_db()
    with db.session_scope() as session:
        session.query(PaperStats).filter(
            PaperStats.arxiv_id == "test.0001"
        ).delete()
    yield
    with db.session_scope() as session:
        session.query(PaperStats).filter(
            PaperStats.arxiv_id == "test.0001"
        ).delete()
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()


def _row(word_count: int) -> dict:
    return {
        "arxiv_id": "test.0001",
        "title": "T",
        "abstract": "A",
        "word_count": word_count,
        "char_count": 100,
        "alpha_ratio": 0.9,
        "section_count": 3,
        "repeated_line_fraction": 0.0,
        "dropped_headings": [],
        "missing_title": False,
        "missing_abstract": False,
        "tei_key": "extracted/test.0001.tei.xml",
        "text_key": "transformed/test.0001.txt",
        "stats_key": None,
    }


def test_upsert_is_idempotent(_clean_db):
    db.upsert_paper_stats(_row(100))
    db.upsert_paper_stats(_row(200))  # same arxiv_id -> update, not insert

    with db.session_scope() as session:
        rows = session.query(PaperStats).filter(
            PaperStats.arxiv_id == "test.0001"
        ).all()
        assert len(rows) == 1
        assert rows[0].word_count == 200
        assert rows[0].updated_at >= rows[0].created_at
