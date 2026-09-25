"""Coverage & service charts."""

from __future__ import annotations

import plotly.graph_objects as go

from vehicle_routing_web.domain.scenario import PRIORITIES
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.visualization import common


def build_coverage_donut(solution: Solution) -> go.Figure:
    served = solution.metrics.served
    omitted = solution.metrics.omitted
    total = served + omitted
    if total == 0:
        return common.empty_figure("No employees in this solution.")
    pct = solution.response.service_level_pct
    fig = go.Figure(
        go.Pie(
            labels=["Served", "Omitted"],
            values=[served, omitted],
            hole=0.6,
            marker={"colors": [common.GREEN, common.RED]},
            textinfo="label+value+percent",
            sort=False,
            direction="clockwise",
            hovertemplate="%{label}: %{value} employees (%{percent})<extra></extra>",
        )
    )
    fig.add_annotation(text=f"<b>{pct:.1f}%</b><br>served", x=0.5, y=0.5, showarrow=False, font={"size": 18})
    return common.base_layout(fig, "Service coverage", height=340).update_layout(showlegend=False)


def omitted_counts(solution: Solution) -> dict[str, int]:
    r = solution.response
    return {
        "low": r.omitted_low_priority_count,
        "medium": r.omitted_medium_priority_count,
        "high": r.omitted_high_priority_count,
    }


def build_omitted_by_priority(solution: Solution) -> go.Figure:
    counts = omitted_counts(solution)
    total = sum(counts.values())
    if total == 0:
        return common.empty_figure("No omitted employees.")
    fig = go.Figure(
        go.Bar(
            x=[f"{common.PRIORITY_LABELS[p]} priority" for p in PRIORITIES],
            y=[counts[p] for p in PRIORITIES],
            marker={"color": [common.PRIORITY_COLORS[p] for p in PRIORITIES]},
            text=[str(counts[p]) for p in PRIORITIES],
            textposition="outside",
            customdata=[[counts[p] / total * 100] for p in PRIORITIES],
            hovertemplate="%{x}: %{y} omitted (%{customdata[0]:.1f}% of omitted)<extra></extra>",
        )
    )
    fig.update_yaxes(title_text="Omitted employees", rangemode="tozero", dtick=1)
    return common.base_layout(fig, "Omitted employees by priority", height=340).update_layout(showlegend=False)


def build_omitted_map(solution: Solution) -> go.Figure:
    omitted = solution.omitted_employees
    if not omitted:
        return common.empty_figure("No omitted employees to locate.", height=420)
    fig = go.Figure()
    for priority in PRIORITIES:
        subset = [e for e in omitted if e.priority == priority]
        if not subset:
            continue
        fig.add_trace(
            go.Scatter(
                x=[e.x for e in subset],
                y=[e.y for e in subset],
                mode="markers+text",
                text=[e.label for e in subset],
                textposition="top center",
                marker={
                    "size": 13,
                    "color": common.PRIORITY_COLORS[priority],
                    "symbol": {"low": "circle", "medium": "square", "high": "diamond"}[priority],
                    "line": {"width": 1, "color": "#2C3E50"},
                },
                customdata=[[e.node_id, e.label, e.priority] for e in subset],
                hovertemplate=(
                    "%{customdata[1]} (node %{customdata[0]})<br>Priority: %{customdata[2]}"
                    "<br>x=%{x:.2f} km, y=%{y:.2f} km<extra></extra>"
                ),
                name=f"{common.PRIORITY_LABELS[priority]} priority",
            )
        )
    fig.update_xaxes(title_text="x (km)")
    fig.update_yaxes(title_text="y (km)", scaleanchor="x", scaleratio=1)
    return common.base_layout(fig, "Omitted employees by location", height=420)
