"""Load balancing & variance charts (active routes only)."""

from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go

from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.visualization import common
from vehicle_routing_web.visualization.efficiency import route_scatter

MATRIX_COLUMNS: tuple[tuple[str, str], ...] = (
    ("modeled_duration_min", "Duration (min)"),
    ("physical_distance_km", "Distance (km)"),
    ("demand_utilization_pct", "Demand util. (%)"),
    ("total_service_stops", "Service stops"),
    ("total_service_time_min", "Service time (min)"),
    ("total_drive_time_min", "Drive time (min)"),
)


@dataclass(frozen=True, slots=True)
class RouteMatrix:
    vehicle_ids: list[int]
    column_labels: list[str]
    absolute: list[list[float]]  # rows = routes, columns = MATRIX_COLUMNS
    normalized: list[list[float]]  # min-max per column, 0..1
    percentile_rank: list[list[float]]  # 0..100 within column


def normalize_column(values: list[float]) -> list[float]:
    """Min-max scaling to 0..1; a constant column maps to 0.0 (no spread to show)."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def rank_column(values: list[float]) -> list[float]:
    """Share of routes (in %) whose value is <= each value."""
    n = len(values)
    return [sum(1 for other in values if other <= v) / n * 100.0 for v in values] if n else []


def build_route_matrix(solution: Solution) -> RouteMatrix:
    routes = sorted(solution.active_routes, key=lambda r: r.vehicle_id)
    columns = [
        [float(r.modeled_route_duration) for r in routes],
        [r.physical_route_distance for r in routes],
        [r.demand_utilization_pct for r in routes],
        [float(r.total_service_stops) for r in routes],
        [float(r.total_service_time_min) for r in routes],
        [float(r.total_drive_time_min) for r in routes],
    ]

    def transpose(cols: list[list[float]]) -> list[list[float]]:
        return [list(row) for row in zip(*cols, strict=True)] if routes else []

    return RouteMatrix(
        vehicle_ids=[r.vehicle_id for r in routes],
        column_labels=[label for _, label in MATRIX_COLUMNS],
        absolute=transpose(columns),
        normalized=transpose([normalize_column(c) for c in columns]),
        percentile_rank=transpose([rank_column(c) for c in columns]),
    )


def build_route_heatmap(solution: Solution) -> go.Figure:
    matrix = build_route_matrix(solution)
    if not matrix.vehicle_ids:
        return common.empty_figure("No active routes.", height=420)
    text = [[f"{v:.1f}" for v in row] for row in matrix.absolute]
    custom = [
        [[matrix.absolute[i][j], matrix.percentile_rank[i][j]] for j in range(len(matrix.column_labels))]
        for i in range(len(matrix.vehicle_ids))
    ]
    fig = go.Figure(
        go.Heatmap(
            z=matrix.normalized,
            x=matrix.column_labels,
            y=[f"Vehicle {v}" for v in matrix.vehicle_ids],
            zmin=0,
            zmax=1,
            colorscale=[[0, common.GREEN], [0.5, common.YELLOW], [1, common.RED]],
            text=text,
            texttemplate="%{text}",
            customdata=custom,
            hovertemplate=(
                "%{y}<br>%{x}: %{customdata[0]:.2f}<br>Percentile rank in column: %{customdata[1]:.0f}"
                "<br>Normalized: %{z:.2f}<extra></extra>"
            ),
            colorbar={"title": "Normalized<br>(0 = column min)"},
        )
    )
    fig.update_yaxes(autorange="reversed")
    return common.base_layout(
        fig, "Route performance matrix (normalized per column)", height=max(320, 60 + 28 * len(matrix.vehicle_ids))
    )


def build_std_bars(solution: Solution) -> go.Figure:
    r = solution.response
    bars = [
        ("Demand balance<br>(std dev, demand units)", r.workload_balance_demand_std, common.TEAL),
        ("Distance balance<br>(std dev, km)", r.workload_balance_distance_std, common.ORANGE),
        ("Duration balance<br>(std dev, min)", r.workload_balance_duration_std, common.PURPLE),
    ]
    fig = go.Figure(
        go.Bar(
            x=[b[0] for b in bars],
            y=[b[1] for b in bars],
            marker={"color": [b[2] for b in bars]},
            text=[f"{b[1]:.2f}" for b in bars],
            textposition="outside",
            hovertemplate="%{x}: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_yaxes(title_text="Population standard deviation", rangemode="tozero")
    return common.base_layout(fig, "Workload balance (lower = more balanced)", height=360).update_layout(
        showlegend=False
    )


def build_duration_vs_demand(solution: Solution) -> go.Figure:
    routes = solution.active_routes
    return route_scatter(
        solution,
        [float(r.modeled_route_duration) for r in routes],
        [float(r.covered_demand) for r in routes],
        title="Route duration vs. covered demand",
        x_title="Route duration",
        y_title="Covered demand",
        x_unit="min",
        y_unit="employees",
    )


def balance_stats(solution: Solution) -> list[tuple[str, str, t.Rating]]:
    """Balance summary panel entries: (label, value text, rating)."""
    r = solution.response
    m = solution.metrics
    ratio = m.max_min_duration_ratio
    return [
        ("Max route duration", f"{r.max_route_duration_min} min", t.Rating.INFO),
        ("Min route duration", f"{r.min_route_duration_min} min", t.Rating.INFO),
        ("Duration spread", f"{r.spread_route_duration_min} min", t.Rating.INFO),
        ("Max/min duration ratio", f"{ratio:.6f}" if ratio is not None else "not available", t.Rating.INFO),
        (
            "Average demand utilization",
            f"{m.mean_demand_utilization_pct:.2f} %",
            t.mid_band_is_good(m.mean_demand_utilization_pct, t.DEMAND_UTILIZATION_BAND, (40.0, 100.0)),
        ),
        (
            "P95 demand utilization",
            f"{m.p95_demand_utilization_pct:.2f} %",
            t.low_is_good(m.p95_demand_utilization_pct, t.P95_DEMAND_UTILIZATION_MAX, float("inf")),
        ),
    ]
