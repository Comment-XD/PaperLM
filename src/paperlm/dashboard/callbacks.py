"""Dash callbacks: filter -> figures/KPIs/table, and export selection -> S3."""

from __future__ import annotations

import json

from dash import Input, Output, State, no_update

from paperlm.dashboard import figures
from paperlm.dashboard.data import build_manifest, filter_df, load_papers


def controls_to_predicate(
    alpha, wordcount, repeat, sections, exclude
) -> dict:
    """Map raw control values to a filter predicate (pure, testable)."""
    exclude = exclude or []
    return {
        "alpha_ratio": alpha,
        "word_count": wordcount,
        "repeated_line_fraction": repeat,
        "section_count": sections,
        "exclude_missing_title": "title" in exclude,
        "exclude_missing_abstract": "abstract" in exclude,
    }


def register_callbacks(app) -> None:
    @app.callback(
        Output("fig-scatter", "figure"),
        Output("fig-wordcount", "figure"),
        Output("fig-alpha", "figure"),
        Output("fig-repeat", "figure"),
        Output("fig-missing", "figure"),
        Output("fig-ecdf", "figure"),
        Output("kpi-count", "children"),
        Output("kpi-words", "children"),
        Output("kpi-tokens", "children"),
        Output("header-summary", "children"),
        Output("paper-table", "data"),
        Output("selected-ids", "data"),
        Input("f-alpha", "value"),
        Input("f-wordcount", "value"),
        Input("f-repeat", "value"),
        Input("f-sections", "value"),
        Input("f-exclude", "value"),
        Input("f-logx", "value"),
    )
    def _update(alpha, wordcount, repeat, sections, exclude, logx):
        predicate = controls_to_predicate(alpha, wordcount, repeat, sections, exclude)
        df = load_papers()
        selected = filter_df(df, predicate)

        count = len(selected)
        total_words = int(selected["word_count"].sum()) if count else 0
        est_tokens = int(total_words * 1.3)
        log_x = bool(logx)

        table_cols = [
            "arxiv_id",
            "title",
            "word_count",
            "alpha_ratio",
            "repeated_line_fraction",
        ]
        present = [c for c in table_cols if c in selected.columns]
        table_data = selected[present].to_dict("records") if count else []
        selected_ids = selected["arxiv_id"].tolist() if count else []

        return (
            figures.quality_scatter(selected),
            figures.word_count_hist(selected, log_x=log_x),
            figures.alpha_ratio_hist(selected),
            figures.repeated_fraction_hist(selected),
            figures.missing_bar(selected),
            figures.word_count_ecdf(selected),
            f"{count:,}",
            f"{total_words:,}",
            f"{est_tokens:,}",
            f"{count:,} of {len(df):,} papers selected",
            table_data,
            selected_ids,
        )

    @app.callback(
        Output("export-status", "children"),
        Input("export-btn", "n_clicks"),
        State("selected-ids", "data"),
        State("sel-name", "value"),
        State("f-alpha", "value"),
        State("f-wordcount", "value"),
        State("f-repeat", "value"),
        State("f-sections", "value"),
        State("f-exclude", "value"),
        prevent_initial_call=True,
    )
    def _export(n_clicks, selected_ids, name, alpha, wordcount, repeat, sections, exclude):
        if not n_clicks:
            return no_update
        name = (name or "selection").strip()
        if not selected_ids:
            return "No papers selected — adjust the filters first."

        # Imported lazily so the module imports without boto3 configured.
        from paperlm.config import get_settings
        from paperlm.storage import upload_bytes

        predicate = controls_to_predicate(alpha, wordcount, repeat, sections, exclude)
        manifest = build_manifest(selected_ids, predicate, name)
        key = f"{get_settings().selections_prefix}{name}.json"
        upload_bytes(
            key, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        )
        return f"Saved {len(selected_ids):,} papers → {key}  (make tokenize SELECTION={key})"
