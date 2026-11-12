"""Unit tests for the pure Stats -> paper_stats row mapping."""

from paperlm.db_models import PaperStats, stats_to_row
from paperlm.models import Stats, TransformResult


def _result() -> TransformResult:
    return TransformResult(
        title="Attention Is All You Need",
        abstract="We propose the Transformer.",
        text="body",
        stats=Stats(
            word_count=1200,
            char_count=7000,
            alpha_ratio=0.82,
            section_count=6,
            repeated_line_fraction=0.03,
            dropped_headings=["references", "acknowledgements"],
            missing_title=False,
            missing_abstract=False,
        ),
    )


def test_stats_to_row_maps_all_fields():
    row = stats_to_row(
        "2606.15253",
        _result(),
        tei_key="extracted/2606.15253.tei.xml",
        text_key="transformed/2606.15253.txt",
        stats_key="transformed/2606.15253.stats.json",
    )

    assert row["arxiv_id"] == "2606.15253"
    assert row["title"] == "Attention Is All You Need"
    assert row["word_count"] == 1200
    assert row["alpha_ratio"] == 0.82
    assert row["dropped_headings"] == ["references", "acknowledgements"]
    assert row["missing_abstract"] is False
    assert row["tei_key"] == "extracted/2606.15253.tei.xml"
    assert row["stats_key"] == "transformed/2606.15253.stats.json"


def test_stats_to_row_keys_are_valid_columns():
    # Every key must be a real column on the model (keeps the mapping honest).
    columns = set(PaperStats.__table__.columns.keys())
    row = stats_to_row("x", _result(), "t", "tx", None)
    assert set(row).issubset(columns)
    # Token columns are left for the tokenize stage, not set here.
    assert "token_count" not in row
