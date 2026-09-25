"""Dashboard header: title, solver status, metadata and the always-visible executive summary."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.presentation.dashboard.components import rating_badge, stat_card

_STATUS_RATING = {
    "OPTIMAL": t.Rating.GOOD,
    "FEASIBLE": t.Rating.GOOD,
    "TIMEOUT": t.Rating.WARNING,
}

_SEMAPHORE_TEXT = {
    t.Rating.GOOD: "Green: service level at or above 95%",
    t.Rating.WARNING: "Amber: service level between 85% and 95%",
    t.Rating.BAD: "Red: service level below 85%",
}


def status_rating(status: str) -> t.Rating:
    return _STATUS_RATING.get(status, t.Rating.BAD)


def build_header(solution: Solution) -> html.Div:
    r = solution.response
    return html.Div(
        [
            html.H1(f"Solution dashboard: {solution.process_id}", className="h3 mb-2"),
            dbc.Stack(
                [
                    rating_badge(status_rating(r.status), f"Solver status: {r.status}"),
                    html.Span(f"Detail: {r.solver_status_detail}", className="small"),
                    html.Span(
                        f"Solution generated: {solution.generated_at:%Y-%m-%d %H:%M} UTC", className="small text-muted"
                    ),
                    html.Span(f"Search time: {r.search_wall_time_ms:,} ms", className="small text-muted"),
                ],
                direction="horizontal",
                gap=3,
                class_name="flex-wrap align-items-center mb-3",
            ),
            *_hints(r.infeasibility_hints),
        ]
    )


def _hints(hints: list[str]) -> list[Any]:
    if not hints:
        return []
    return [
        dbc.Alert(
            [html.Strong("Infeasibility hints"), html.Ul([html.Li(h) for h in hints[:10]], className="mb-0")],
            color="warning",
        )
    ]


def build_executive_summary(solution: Solution) -> html.Section:
    r = solution.response
    m = solution.metrics
    semaphore = t.service_level_rating(r.service_level_pct)
    omitted_pct = (m.omitted / m.total_employees * 100) if m.total_employees else 0.0
    cards = [
        stat_card("Status", r.status, badge=rating_badge(status_rating(r.status))),
        stat_card("Search time", f"{r.search_wall_time_ms:,} ms", note="Wall-clock solver time"),
        stat_card(
            "Service level",
            f"{r.service_level_pct:.1f} %",
            note=f"{m.served} of {m.total_employees} employees served",
            badge=rating_badge(semaphore),
        ),
        stat_card("Omitted employees", f"{m.omitted}", note=f"{omitted_pct:.1f} % of employees"),
        stat_card("Total distance", f"{r.total_physical_route_distance:,.1f} km", note="Physical, all routes"),
        stat_card("Total duration", f"{m.total_modeled_duration_min:,.0f} min", note="Sum of modelled route durations"),
        stat_card("Objective value", f"{r.total_objective_value:,}"),
        stat_card(
            "Fleet utilization",
            f"{r.fleet_utilization_pct:.1f} %",
            note=f"{m.routes_active} of {m.routes_total} vehicles used",
        ),
    ]
    return html.Section(
        [
            html.H2("Executive summary", className="h5"),
            dbc.Alert(
                _SEMAPHORE_TEXT[semaphore],
                color={"good": "success", "warning": "warning", "bad": "danger"}[semaphore.value],
                class_name="py-2",
            ),
            dbc.Row(cards),
        ],
        **{"aria-label": "Executive summary"},
    )
