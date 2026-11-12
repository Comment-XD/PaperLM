"""A clean, white, high-detail Plotly template registered as the default.

Minimal chrome, light gridlines, restrained accent palette, roomy margins --
the plots carry the detail, the frame stays quiet.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

TEMPLATE_NAME = "paperlm_white"

# Restrained accent + a muted sequential for the continuous color dimension.
ACCENT = "#2563EB"       # calm blue
ACCENT_MUTED = "#64748B"  # slate
SEQUENTIAL = "Blues"
GRID = "#ECECEC"
AXIS = "#CBD5E1"
TEXT = "#1F2933"
FONT = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)


def _template() -> go.layout.Template:
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family=FONT, size=13, color=TEXT),
        title=dict(font=dict(size=15, color=TEXT), x=0.01, xanchor="left"),
        margin=dict(l=56, r=24, t=48, b=48),
        colorway=[ACCENT, ACCENT_MUTED, "#0EA5E9", "#F59E0B", "#10B981", "#EF4444"],
        hovermode="closest",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=AXIS, font_size=12),
        xaxis=dict(
            gridcolor=GRID,
            zerolinecolor=GRID,
            linecolor=AXIS,
            ticks="outside",
            tickcolor=AXIS,
            automargin=True,
        ),
        yaxis=dict(
            gridcolor=GRID,
            zerolinecolor=GRID,
            linecolor=AXIS,
            ticks="outside",
            tickcolor=AXIS,
            automargin=True,
        ),
        colorscale=dict(sequential=SEQUENTIAL),
        bargap=0.06,
    )
    return template


def register() -> str:
    """Register the template and make it the default; return its name."""
    pio.templates[TEMPLATE_NAME] = _template()
    pio.templates.default = TEMPLATE_NAME
    return TEMPLATE_NAME
