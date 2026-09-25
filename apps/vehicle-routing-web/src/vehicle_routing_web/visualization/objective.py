"""Objective diagnostics: decomposition chart and validation alerts."""

from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go

from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.visualization import common


def build_objective_donut(solution: Solution) -> go.Figure:
    r = solution.response
    parts = [
        ("Travel cost", r.objective_travel_cost, common.BLUE),
        ("Omission penalty", r.objective_omission_penalty, common.RED),
        ("Unattributed cost", r.objective_unattributed_cost, common.GRAY),
    ]
    if r.total_objective_value <= 0 or all(v == 0 for _, v, _ in parts):
        return common.empty_figure("Objective value is zero; nothing to decompose.")
    fig = go.Figure(
        go.Pie(
            labels=[p[0] for p in parts],
            values=[p[1] for p in parts],
            marker={"colors": [p[2] for p in parts]},
            hole=0.6,
            sort=False,
            textinfo="label+percent",
            hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{r.total_objective_value:,}</b><br>total", x=0.5, y=0.5, showarrow=False, font={"size": 16}
    )
    return common.base_layout(fig, "Objective decomposition", height=360).update_layout(showlegend=False)


@dataclass(frozen=True, slots=True)
class ObjectiveAlert:
    level: t.Rating  # BAD -> red flag, WARNING -> amber, INFO -> info, GOOD -> green
    message: str


def objective_alerts(solution: Solution) -> list[ObjectiveAlert]:
    r = solution.response
    share = solution.metrics.unattributed_cost_share
    alerts: list[ObjectiveAlert] = []
    if share is not None and share > t.UNATTRIBUTED_RED_SHARE:
        alerts.append(ObjectiveAlert(t.Rating.BAD, "Unattributed cost is significant - review solution quality."))
    if r.solver_failures > t.SOLVER_FAILURES_WARNING:
        alerts.append(ObjectiveAlert(t.Rating.WARNING, "High solver failure count - solution may be near boundary."))
    alerts.append(ObjectiveAlert(t.Rating.INFO, f"Search completed in {r.search_wall_time_ms:,} ms."))
    if share is not None and share < t.UNATTRIBUTED_GREEN_SHARE:
        alerts.append(ObjectiveAlert(t.Rating.GOOD, "Solution objective is well-explained by the model."))
    return alerts
