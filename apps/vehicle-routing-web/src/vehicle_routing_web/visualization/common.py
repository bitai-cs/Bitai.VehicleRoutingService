"""Colours and helpers shared by all figure builders (no Dash imports)."""

from __future__ import annotations

import plotly.graph_objects as go

# Route palette: Okabe-Ito (colour-blind safe) followed by extra distinguishable hues.
ROUTE_COLORS: tuple[str, ...] = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
    "#8C564B",
    "#7F7F7F",
    "#9467BD",
    "#17BECF",
    "#BCBD22",
    "#1B9E77",
    "#E377C2",
    "#AA3377",
    "#332288",
)

GREEN = "#2ECC71"
AMBER = "#F39C12"
YELLOW = "#F1C40F"
RED = "#E74C3C"
BLUE = "#3498DB"
GRAY = "#95A5A6"
TEAL = "#1ABC9C"
ORANGE = "#E67E22"
PURPLE = "#8E44AD"
LIGHT_GRAY = "#D5D8DC"

PRIORITY_COLORS: dict[str, str] = {"low": BLUE, "medium": YELLOW, "high": RED}
PRIORITY_LABELS: dict[str, str] = {"low": "Low", "medium": "Medium", "high": "High"}


def route_color(vehicle_id: int) -> str:
    return ROUTE_COLORS[vehicle_id % len(ROUTE_COLORS)]


def empty_figure(message: str, *, height: int = 320) -> go.Figure:
    """A figure with an explanatory message instead of empty axes."""
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font={"size": 14})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=height, margin={"l": 20, "r": 20, "t": 20, "b": 20})
    return fig


def base_layout(fig: go.Figure, title: str, *, height: int = 360) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.01, "font": {"size": 15}},
        height=height,
        margin={"l": 55, "r": 20, "t": 50, "b": 50},
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "top", "y": -0.2},
    )
    return fig
