"""Figure builders: a filtered DataFrame in, a styled ``go.Figure`` out.

Each builder is pure and renders under the registered ``paperlm_white`` default
template. They tolerate an empty DataFrame (returning an empty-state figure).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _empty(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[
            dict(
                text="No papers match the current filters",
                showarrow=False,
                font=dict(color="#94A3B8", size=13),
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )
        ],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def word_count_hist(df: pd.DataFrame, log_x: bool = False) -> go.Figure:
    """Distribution of word counts (optionally log-scaled x)."""
    if df.empty:
        return _empty("Word count distribution")
    fig = px.histogram(df, x="word_count", nbins=50, log_x=log_x)
    fig.update_layout(
        title="Word count distribution",
        xaxis_title="words per paper",
        yaxis_title="papers",
    )
    return fig


def alpha_ratio_hist(df: pd.DataFrame) -> go.Figure:
    """Distribution of alphabetic-character ratio (an extraction-cleanliness cue)."""
    if df.empty:
        return _empty("Alphabetic ratio distribution")
    fig = px.histogram(df, x="alpha_ratio", nbins=40)
    fig.update_layout(
        title="Alphabetic ratio distribution",
        xaxis_title="alpha ratio",
        yaxis_title="papers",
    )
    return fig


def quality_scatter(df: pd.DataFrame) -> go.Figure:
    """Word count vs alpha ratio, colored by repeated-line fraction.

    The high-detail centerpiece: each point is a paper, hover shows its id and
    title, color flags likely extraction noise (high repeated-line fraction).
    """
    if df.empty:
        return _empty("Word count vs alpha ratio")
    hover = {
        "arxiv_id": True,
        "repeated_line_fraction": ":.3f",
        "word_count": ":,",
        "alpha_ratio": ":.3f",
    }
    if "title" in df.columns:
        hover["title"] = True
    fig = px.scatter(
        df,
        x="word_count",
        y="alpha_ratio",
        color="repeated_line_fraction",
        color_continuous_scale="Blues",
        hover_data=hover,
        opacity=0.75,
    )
    fig.update_traces(marker=dict(size=7, line=dict(width=0.4, color="#FFFFFF")))
    fig.update_layout(
        title="Word count vs alpha ratio",
        xaxis_title="words per paper",
        yaxis_title="alpha ratio",
        coloraxis_colorbar_title="repeat frac",
    )
    return fig


def repeated_fraction_hist(df: pd.DataFrame) -> go.Figure:
    """Distribution of repeated-line fraction (duplicated-prose signal)."""
    if df.empty:
        return _empty("Repeated-line fraction")
    fig = px.histogram(df, x="repeated_line_fraction", nbins=40)
    fig.update_layout(
        title="Repeated-line fraction",
        xaxis_title="repeated line fraction",
        yaxis_title="papers",
    )
    return fig


def missing_bar(df: pd.DataFrame) -> go.Figure:
    """Counts of papers missing a title / abstract."""
    if df.empty:
        return _empty("Missing metadata")
    counts = {
        "missing title": int(df["missing_title"].astype(bool).sum()),
        "missing abstract": int(df["missing_abstract"].astype(bool).sum()),
    }
    fig = go.Figure(
        go.Bar(x=list(counts), y=list(counts.values()), marker_color="#2563EB")
    )
    fig.update_layout(
        title="Missing metadata",
        yaxis_title="papers",
    )
    return fig


def word_count_ecdf(df: pd.DataFrame) -> go.Figure:
    """Empirical CDF of word counts -- helps pick slider thresholds."""
    if df.empty:
        return _empty("Word count ECDF")
    fig = px.ecdf(df, x="word_count")
    fig.update_layout(
        title="Word count ECDF",
        xaxis_title="words per paper",
        yaxis_title="cumulative fraction",
    )
    return fig
