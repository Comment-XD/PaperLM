"""Dash app entrypoint: layout + wiring. Exposes ``server`` for gunicorn."""

from __future__ import annotations

import pandas as pd
from dash import Dash, dash_table, dcc, html

from paperlm.dashboard import theme
from paperlm.dashboard.callbacks import register_callbacks
from paperlm.dashboard.data import load_papers

theme.register()

TABLE_COLUMNS = [
    "arxiv_id",
    "title",
    "word_count",
    "alpha_ratio",
    "repeated_line_fraction",
]


def _initial_df() -> pd.DataFrame:
    """Load data for slider bounds; tolerate an unreachable/empty DB at startup."""
    try:
        return load_papers()
    except Exception:  # pragma: no cover - startup resilience
        return pd.DataFrame()


def _bounds(df: pd.DataFrame, column: str, default_hi: float) -> tuple[float, float]:
    if df.empty or column not in df.columns or df[column].isna().all():
        return (0.0, default_hi)
    return (float(df[column].min()), float(df[column].max()))


def _range_control(label, cid, low, high, step, value):
    return html.Div(
        className="control",
        children=[
            html.Label(label, className="control-label"),
            dcc.RangeSlider(
                id=cid,
                min=low,
                max=high,
                step=step,
                value=value,
                marks=None,
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ],
    )


def build_layout(df: pd.DataFrame) -> html.Div:
    wc_lo, wc_hi = _bounds(df, "word_count", 20000)
    sc_lo, sc_hi = _bounds(df, "section_count", 30)

    controls = html.Div(
        className="rail",
        children=[
            html.H2("Curate corpus", className="rail-title"),
            html.P(
                "Filter by quality, then export the selection for tokenization.",
                className="rail-sub",
            ),
            _range_control("Alpha ratio", "f-alpha", 0, 1, 0.01, [0, 1]),
            _range_control(
                "Word count", "f-wordcount", wc_lo, wc_hi, 1, [wc_lo, wc_hi]
            ),
            _range_control(
                "Repeated-line fraction", "f-repeat", 0, 1, 0.01, [0, 1]
            ),
            _range_control(
                "Section count", "f-sections", sc_lo, sc_hi, 1, [sc_lo, sc_hi]
            ),
            html.Div(
                className="control",
                children=[
                    dcc.Checklist(
                        id="f-exclude",
                        options=[
                            {"label": " Exclude missing title", "value": "title"},
                            {
                                "label": " Exclude missing abstract",
                                "value": "abstract",
                            },
                        ],
                        value=[],
                        className="checklist",
                    ),
                    dcc.Checklist(
                        id="f-logx",
                        options=[{"label": " Log-scale word count", "value": "log"}],
                        value=[],
                        className="checklist",
                    ),
                ],
            ),
            html.Hr(),
            html.Label("Selection name", className="control-label"),
            dcc.Input(
                id="sel-name",
                type="text",
                value="high_quality_v1",
                className="text-input",
            ),
            html.Button("Export selection", id="export-btn", className="btn"),
            html.Div(id="export-status", className="export-status"),
        ],
    )

    kpis = html.Div(
        className="kpi-row",
        children=[
            html.Div(
                className="kpi",
                children=[
                    html.Div("Selected papers", className="kpi-label"),
                    html.Div("0", id="kpi-count", className="kpi-value"),
                ],
            ),
            html.Div(
                className="kpi",
                children=[
                    html.Div("Total words", className="kpi-label"),
                    html.Div("0", id="kpi-words", className="kpi-value"),
                ],
            ),
            html.Div(
                className="kpi",
                children=[
                    html.Div("Est. tokens (~1.3×)", className="kpi-label"),
                    html.Div("0", id="kpi-tokens", className="kpi-value"),
                ],
            ),
        ],
    )

    grid = html.Div(
        className="plot-grid",
        children=[
            dcc.Graph(id="fig-scatter", className="plot plot-wide"),
            dcc.Graph(id="fig-wordcount", className="plot"),
            dcc.Graph(id="fig-alpha", className="plot"),
            dcc.Graph(id="fig-repeat", className="plot"),
            dcc.Graph(id="fig-missing", className="plot"),
            dcc.Graph(id="fig-ecdf", className="plot plot-wide"),
        ],
    )

    table = dash_table.DataTable(
        id="paper-table",
        columns=[{"name": c, "id": c} for c in TABLE_COLUMNS],
        page_size=12,
        sort_action="native",
        style_as_list_view=True,
        style_header={"fontWeight": "600", "backgroundColor": "#F8FAFC"},
        style_cell={
            "fontFamily": theme.FONT,
            "fontSize": "13px",
            "textAlign": "left",
            "padding": "8px 10px",
            "maxWidth": "320px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
    )

    return html.Div(
        className="app",
        children=[
            html.Header(
                className="topbar",
                children=[
                    html.H1("PaperLM · Quality", className="brand"),
                    html.Div(id="header-summary", className="header-summary"),
                ],
            ),
            html.Div(
                className="body",
                children=[
                    controls,
                    html.Main(
                        className="main",
                        children=[kpis, grid, html.Div(table, className="table-wrap")],
                    ),
                ],
            ),
            dcc.Store(id="selected-ids"),
        ],
    )


app = Dash(__name__, title="PaperLM Quality")
app.layout = build_layout(_initial_df())
register_callbacks(app)
server = app.server  # gunicorn entrypoint


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
