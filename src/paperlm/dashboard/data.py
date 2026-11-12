"""Data access + pure filtering/selection logic for the dashboard.

The filtering and manifest-building are pure functions (no DB, no Dash) so they
unit-test without a browser or a database. ``load_papers`` is the only piece
that touches the DB.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

# Columns the dashboard reads; keep in sync with db_models.PaperStats.
NUMERIC_RANGES = (
    "alpha_ratio",
    "word_count",
    "repeated_line_fraction",
    "section_count",
)


def load_papers(engine=None) -> pd.DataFrame:
    """Load the whole ``paper_stats`` table into a DataFrame.

    At this corpus size, loading once and filtering in pandas keeps the UI
    instant; push predicates into SQL ``WHERE`` if the corpus grows large.
    """
    if engine is None:
        from paperlm.db import get_engine

        engine = get_engine()
    return pd.read_sql("SELECT * FROM paper_stats", engine)


def filter_df(df: pd.DataFrame, predicate: dict) -> pd.DataFrame:
    """Return the rows of ``df`` matching ``predicate``.

    Predicate schema::

        {
          "alpha_ratio": [min, max],
          "word_count": [min, max],
          "repeated_line_fraction": [min, max],
          "section_count": [min, max],
          "exclude_missing_title": bool,
          "exclude_missing_abstract": bool,
        }

    Any key may be omitted. Missing columns are ignored so an empty/partial
    DataFrame does not raise.
    """
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)
    for column in NUMERIC_RANGES:
        bounds = predicate.get(column)
        if bounds and column in df.columns:
            low, high = bounds
            if low is not None:
                mask &= df[column] >= low
            if high is not None:
                mask &= df[column] <= high

    if predicate.get("exclude_missing_title") and "missing_title" in df.columns:
        mask &= ~df["missing_title"].astype(bool)
    if (
        predicate.get("exclude_missing_abstract")
        and "missing_abstract" in df.columns
    ):
        mask &= ~df["missing_abstract"].astype(bool)

    return df[mask]


def build_manifest(arxiv_ids: list[str], predicate: dict, name: str) -> dict:
    """Build a selection manifest (the dashboard -> tokenize contract).

    Pure: the export callback just serializes this and uploads it to S3 under
    the selections prefix. ``arxiv_ids`` is the frozen selection the tokenize
    job consumes; ``predicate`` is kept for provenance/reproducibility.
    """
    return {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filter": predicate,
        "arxiv_ids": list(arxiv_ids),
        "count": len(arxiv_ids),
    }
