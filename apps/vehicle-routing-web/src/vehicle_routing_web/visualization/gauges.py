"""Gauge figures with the colour bands from the specification."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import plotly.graph_objects as go

from vehicle_routing_web.domain.thresholds import Rating
from vehicle_routing_web.visualization import common


@dataclass(frozen=True, slots=True)
class Band:
    low: float
    high: float
    color: str
    label: str
    rating: Rating


SERVICE_LEVEL_BANDS = (
    Band(0, 60, common.RED, "Critical (<60%)", Rating.BAD),
    Band(60, 85, common.AMBER, "Warning (60-85%)", Rating.WARNING),
    Band(85, 95, common.YELLOW, "Good (85-95%)", Rating.GOOD),
    Band(95, 100, common.GREEN, "Excellent (>=95%)", Rating.GOOD),
)

FLEET_UTILIZATION_BANDS = (
    Band(0, 40, common.RED, "Underutilized (<40%)", Rating.BAD),
    Band(40, 60, common.AMBER, "Moderate (40-60%)", Rating.WARNING),
    Band(60, 90, common.GREEN, "Optimal (60-90%)", Rating.GOOD),
    Band(90, 100, common.BLUE, "Highly utilized (>90%)", Rating.INFO),
)


def cv_bands(axis_max: float) -> tuple[Band, ...]:
    return (
        Band(0.0, 0.3, common.GREEN, "Excellent balance (<=0.30)", Rating.GOOD),
        Band(0.3, 0.5, common.AMBER, "Acceptable (0.30-0.50)", Rating.WARNING),
        Band(0.5, axis_max, common.RED, "Poor balance (>0.50)", Rating.BAD),
    )


def cv_axis_max(value: float) -> float:
    """Axis upper bound: at least 1.0, grown in 0.5 steps so the needle stays on the scale."""
    return max(1.0, math.ceil(value * 1.1 / 0.5) * 0.5)


def band_of(value: float, bands: Sequence[Band]) -> Band:
    for band in bands:
        if band.low <= value < band.high:
            return band
    return bands[-1] if value >= bands[-1].high else bands[0]


def band_label(value: float, bands: Sequence[Band]) -> str:
    """Text name of the band containing ``value`` (so status is not colour-only)."""
    return band_of(value, bands).label


def band_rating(value: float, bands: Sequence[Band]) -> Rating:
    return band_of(value, bands).rating


def build_gauge(
    value: float,
    title: str,
    bands: Sequence[Band],
    *,
    target: float | None = None,
    suffix: str = "",
    decimals: int = 1,
) -> go.Figure:
    axis_max = bands[-1].high
    gauge: dict = {
        "axis": {"range": [bands[0].low, axis_max]},
        "bar": {"color": "#2C3E50", "thickness": 0.25},
        "steps": [{"range": [b.low, b.high], "color": b.color} for b in bands],
    }
    if target is not None:
        gauge["threshold"] = {"line": {"color": "#000000", "width": 4}, "thickness": 0.9, "value": target}
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": suffix, "valueformat": f".{decimals}f"},
            title={
                "text": title
                + (f"<br><span style='font-size:0.8em'>Target: {target:g}{suffix}</span>" if target is not None else "")
            },
            gauge=gauge,
        )
    )
    return common.base_layout(fig, "", height=300).update_layout(
        title=None, margin={"l": 30, "r": 30, "t": 80, "b": 20}
    )
