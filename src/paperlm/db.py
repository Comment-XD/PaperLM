"""Database access: a cached engine/session plus idempotent upsert helpers.

Mirrors ``storage.py`` -- the engine and sessionmaker are built once from
``get_settings()`` and cached. Celery workers each call :func:`upsert_paper_stats`
for their own paper; ``ON CONFLICT (arxiv_id)`` makes the write idempotent and
distinct papers touch distinct rows, so scaled workers never contend.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from paperlm.config import get_settings
from paperlm.db_models import Base, PaperStats


@lru_cache
def get_engine() -> Engine:
    """Return the cached SQLAlchemy engine (built from settings on first call)."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    """Return the cached sessionmaker bound to the engine."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Yield a session, committing on success and rolling back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they do not exist (idempotent)."""
    Base.metadata.create_all(get_engine())


def upsert_paper_stats(row: dict) -> None:
    """Insert or update one ``paper_stats`` row, keyed on ``arxiv_id``.

    Idempotent: re-running the pipeline for a paper overwrites the quality
    columns and bumps ``updated_at`` without touching ``created_at``.
    """
    # Update every supplied column except the identity and created_at.
    update_cols = {
        key: row[key] for key in row if key not in ("arxiv_id", "created_at")
    }
    update_cols["updated_at"] = func.now()

    statement = insert(PaperStats).values(**row)
    statement = statement.on_conflict_do_update(
        index_elements=["arxiv_id"],
        set_=update_cols,
    )
    with session_scope() as session:
        session.execute(statement)


def update_token_counts(rows: Sequence[dict]) -> None:
    """Set token columns (``token_count``/``tokenizer``/``tokenized_at``) per paper.

    Each row must carry ``arxiv_id``; only the token columns present are written.
    Used by the tokenize stage after packing a shard. Rows for unknown
    ``arxiv_id``s are ignored (the paper must already exist from transform).
    """
    if not rows:
        return
    with session_scope() as session:
        for row in rows:
            arxiv_id = row["arxiv_id"]
            values = {k: v for k, v in row.items() if k != "arxiv_id"}
            session.query(PaperStats).filter(
                PaperStats.arxiv_id == arxiv_id
            ).update(values, synchronize_session=False)
