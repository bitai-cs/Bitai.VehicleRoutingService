"""Operational efficiency charts (active routes only)."""

from __future__ import annotations

import plotly.graph_objects as go

from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.visualization import common

MAX_TOTAL_LABELS = 40  # bar-total annotations are skipped above this many routes


def build_distribution(
    vehicle_ids: list[int],
    values: list[float],
    *,
    title: str,
    y_title: str,
    unit: str,
    reference_min: float | None = None,
    reference_max: float | None = None,
    note: str | None = None,
) -> go.Figure:
    if not values:
        return common.empty_figure("No active routes.")
    fig = go.Figure(
        go.Box(
            y=values,
            boxpoints="all",
            jitter=0.4,
            pointpos=0,
            name="Active routes",
            marker={"color": common.BLUE},
            customdata=vehicle_ids,
            hovertemplate=f"Vehicle %{{customdata}}: %{{y:.2f}} {unit}<extra></extra>",
        )
    )
    if reference_max is not None:
        fig.add_hline(
            y=reference_max, line={"color": common.RED, "dash": "dash"}, annotation_text=f"Max {reference_max:g} {unit}"
        )
    if reference_min is not None:
        fig.add_hline(
            y=reference_min,
            line={"color": common.BLUE, "dash": "dot"},
            annotation_text=f"Min {reference_min:g} {unit}",
            annotation_position="bottom right",
        )
    if note:
        fig.add_annotation(text=note, x=1, y=1.08, xref="paper", yref="paper", showarrow=False, xanchor="right")
    fig.update_yaxes(title_text=y_title)
    return common.base_layout(fig, title, height=360).update_layout(showlegend=False)


def build_duration_distribution(solution: Solution) -> go.Figure:
    routes = solution.active_routes
    ratio = solution.metrics.max_min_duration_ratio
    return build_distribution(
        [r.vehicle_id for r in routes],
        [float(r.modeled_route_duration) for r in routes],
        title="Route duration distribution",
        y_title="Modelled route duration (min)",
        unit="min",
        reference_min=float(solution.response.min_route_duration_min) if routes else None,
        reference_max=float(solution.response.max_route_duration_min) if routes else None,
        note=f"Max/min ratio: {ratio:.2f}x" if ratio is not None else "Max/min ratio: not available",
    )


def build_distance_distribution(solution: Solution) -> go.Figure:
    routes = solution.active_routes
    values = [r.physical_route_distance for r in routes]
    note = (
        f"Min {min(values):.1f} / max {max(values):.1f} / spread {max(values) - min(values):.1f} km" if values else None
    )
    return build_distribution(
        [r.vehicle_id for r in routes],
        values,
        title="Route distance distribution",
        y_title="Physical route distance (km)",
        unit="km",
        reference_min=min(values) if values else None,
        reference_max=max(values) if values else None,
        note=note,
    )


def route_scatter(
    solution: Solution,
    x_values: list[float],
    y_values: list[float],
    *,
    title: str,
    x_title: str,
    y_title: str,
    x_unit: str,
    y_unit: str,
) -> go.Figure:
    routes = solution.active_routes
    if not routes:
        return common.empty_figure("No active routes.")
    fig = go.Figure(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers+text",
            text=[str(r.vehicle_id) for r in routes],
            textposition="top center",
            marker={
                "size": [10 + 3 * r.total_service_stops for r in routes],
                "color": [common.route_color(r.vehicle_id) for r in routes],
                "line": {"width": 1, "color": "#2C3E50"},
                "opacity": 0.85,
            },
            customdata=[[r.vehicle_id, r.total_service_stops] for r in routes],
            hovertemplate=(
                f"Vehicle %{{customdata[0]}}<br>{x_title}: %{{x:.1f}} {x_unit}<br>{y_title}: %{{y:.1f}} {y_unit}"
                "<br>Service stops: %{customdata[1]}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(title_text=f"{x_title} ({x_unit})" if x_unit else x_title)
    fig.update_yaxes(title_text=f"{y_title} ({y_unit})" if y_unit else y_title)
    return common.base_layout(fig, title, height=380).update_layout(showlegend=False)


def build_utilization_vs_duration(solution: Solution) -> go.Figure:
    routes = solution.active_routes
    fig = route_scatter(
        solution,
        [r.demand_utilization_pct for r in routes],
        [float(r.modeled_route_duration) for r in routes],
        title="Demand utilization vs. route duration",
        x_title="Demand utilization",
        y_title="Route duration",
        x_unit="%",
        y_unit="min",
    )
    if routes:
        p95 = solution.metrics.p95_demand_utilization_pct
        fig.add_vline(x=p95, line={"color": common.RED, "dash": "dash"}, annotation_text=f"P95 {p95:.1f}%")
    return fig


def slack_minutes(duration: int, drive: int, service: int, wait: int) -> int:
    return max(duration - drive - service - wait, 0)


def build_time_composition(solution: Solution) -> go.Figure:
    routes = sorted(solution.active_routes, key=lambda r: r.vehicle_id)
    if not routes:
        return common.empty_figure("No active routes.")
    labels = [f"V{r.vehicle_id}" for r in routes]
    segments = [
        ("Drive", [r.total_drive_time_min for r in routes], common.BLUE),
        ("Service", [r.total_service_time_min for r in routes], common.GREEN),
        ("Wait", [r.total_wait_time_min for r in routes], common.YELLOW),
        (
            "Slack / idle",
            [
                slack_minutes(
                    r.modeled_route_duration, r.total_drive_time_min, r.total_service_time_min, r.total_wait_time_min
                )
                for r in routes
            ],
            common.LIGHT_GRAY,
        ),
    ]
    fig = go.Figure()
    for name, minutes, color in segments:
        fig.add_trace(
            go.Bar(
                x=labels,
                y=minutes,
                name=name,
                marker={"color": color, "line": {"width": 0.5, "color": "#566573"}},
                hovertemplate=f"%{{x}} {name}: %{{y}} min (%{{customdata:.1f}}%)<extra></extra>",
                customdata=[m / max(r.modeled_route_duration, 1) * 100 for m, r in zip(minutes, routes, strict=True)],
            )
        )
    fig.update_layout(barnorm="percent", barmode="stack")
    if len(routes) <= MAX_TOTAL_LABELS:
        for label, route in zip(labels, routes, strict=True):
            fig.add_annotation(
                x=label,
                y=100,
                text=f"{route.modeled_route_duration} min",
                showarrow=False,
                yshift=12,
                font={"size": 10},
            )
    fig.update_yaxes(title_text="Share of route duration (%)")
    fig.update_xaxes(title_text="Vehicle")
    return common.base_layout(fig, "Time composition by route", height=400)
