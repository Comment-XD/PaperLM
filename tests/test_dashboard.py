"""Tests for the dashboard's pure data/figure logic (no browser, no DB).

Skipped entirely if the optional ``dashboard`` dependency group is not installed
(``uv sync --group dashboard``).
"""

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("plotly")

from paperlm.dashboard import figures  # noqa: E402
from paperlm.dashboard.data import build_manifest, filter_df  # noqa: E402


def _df():
    return pd.DataFrame(
        [
            # arxiv_id, word_count, alpha_ratio, repeated, sections, miss_t, miss_a
            ("a", 3000, 0.90, 0.02, 6, False, False),
            ("b", 500, 0.70, 0.30, 2, True, False),
            ("c", 8000, 0.85, 0.05, 9, False, True),
            ("d", 1500, 0.60, 0.15, 4, False, False),
        ],
        columns=[
            "arxiv_id",
            "word_count",
            "alpha_ratio",
            "repeated_line_fraction",
            "section_count",
            "missing_title",
            "missing_abstract",
        ],
    )


def test_filter_df_numeric_ranges():
    out = filter_df(
        _df(),
        {"word_count": [1000, 9000], "alpha_ratio": [0.8, 1.0]},
    )
    assert set(out["arxiv_id"]) == {"a", "c"}


def test_filter_df_repeated_fraction_ceiling():
    out = filter_df(_df(), {"repeated_line_fraction": [0.0, 0.1]})
    assert set(out["arxiv_id"]) == {"a", "c"}


def test_filter_df_exclusions():
    out = filter_df(
        _df(),
        {"exclude_missing_title": True, "exclude_missing_abstract": True},
    )
    assert set(out["arxiv_id"]) == {"a", "d"}


def test_filter_df_empty_in_empty_out():
    empty = pd.DataFrame()
    assert filter_df(empty, {"word_count": [0, 1]}).empty


def test_build_manifest_shape():
    manifest = build_manifest(["a", "c"], {"word_count": [1000, 9000]}, "hq_v1")
    assert manifest["name"] == "hq_v1"
    assert manifest["arxiv_ids"] == ["a", "c"]
    assert manifest["count"] == 2
    assert manifest["filter"] == {"word_count": [1000, 9000]}
    assert "created_at" in manifest


def test_figures_build_without_error():
    df = _df()
    for builder in (
        figures.quality_scatter,
        figures.word_count_hist,
        figures.alpha_ratio_hist,
        figures.repeated_fraction_hist,
        figures.missing_bar,
        figures.word_count_ecdf,
    ):
        fig = builder(df)
        assert fig.data, f"{builder.__name__} produced no traces"


def test_figures_handle_empty_df():
    empty = pd.DataFrame(columns=_df().columns)
    fig = figures.quality_scatter(empty)
    # Empty-state figure: an annotation, no data traces.
    assert fig.layout.annotations
