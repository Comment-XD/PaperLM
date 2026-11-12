"""SQLAlchemy models for the paper-quality metadata store.

One row per paper in ``paper_stats`` -- the queryable source of truth for the
quality signals that ``transform`` produces, plus token counts filled in later
by the tokenize stage. The table is created with ``db.init_db()`` (``create_all``);
there is no migration tool, so every column the pipeline will ever write is
declared here up front (the token columns are nullable until Phase 2 populates
them).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from paperlm.models import TransformResult


class Base(DeclarativeBase):
    """Declarative base for all PaperLM tables."""


class PaperStats(Base):
    """Quality metadata for one paper, keyed by its arXiv id (= file stem)."""

    __tablename__ = "paper_stats"

    # Identity -- the file stem (e.g. "2606.15253"); idempotency key for upserts.
    arxiv_id: Mapped[str] = mapped_column(Text, primary_key=True)

    # Header metadata (nullable; used for dashboard labels/tooltips).
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality signals -- the models.Stats fields.
    word_count: Mapped[int] = mapped_column(Integer, index=True)
    char_count: Mapped[int] = mapped_column(Integer)
    alpha_ratio: Mapped[float] = mapped_column(Float, index=True)
    section_count: Mapped[int] = mapped_column(Integer, index=True)
    repeated_line_fraction: Mapped[float] = mapped_column(Float, index=True)
    dropped_headings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    missing_title: Mapped[bool] = mapped_column(Boolean, index=True)
    missing_abstract: Mapped[bool] = mapped_column(Boolean, index=True)

    # S3 artifact pointers.
    tei_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Filled in by the tokenize stage (Phase 2).
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokenizer: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokenized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Bookkeeping.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_paper_stats_quality", "alpha_ratio", "word_count"),
    )


def stats_to_row(
    arxiv_id: str,
    result: TransformResult,
    tei_key: str,
    text_key: str,
    stats_key: str | None,
) -> dict:
    """Map a TransformResult into the ``paper_stats`` column dict for upsert.

    Pure (no DB, no I/O) so it can be unit-tested with a hand-built result.
    Column keys here must match :class:`PaperStats`; the token columns are left
    for the tokenize stage to fill.
    """
    stats = result.stats
    return {
        "arxiv_id": arxiv_id,
        "title": result.title,
        "abstract": result.abstract,
        "word_count": stats.word_count,
        "char_count": stats.char_count,
        "alpha_ratio": stats.alpha_ratio,
        "section_count": stats.section_count,
        "repeated_line_fraction": stats.repeated_line_fraction,
        "dropped_headings": stats.dropped_headings,
        "missing_title": stats.missing_title,
        "missing_abstract": stats.missing_abstract,
        "tei_key": tei_key,
        "text_key": text_key,
        "stats_key": stats_key,
    }
