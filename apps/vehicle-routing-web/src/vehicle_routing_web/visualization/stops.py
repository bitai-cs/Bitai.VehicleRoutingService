"""Stop-level Gantt timeline for one route."""

from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go

from vehicle_routing_web.domain.solve_response import SolvedRoute
from vehicle_routing_web.visualization import common


@dataclass(frozen=True, slots=True)
class Segment:
    activity: str  # "Drive" | "Wait" | "Service"
    start_min: int
    duration_min: int
    stop_sequence: int
    node_label: str


def route_segments(route: SolvedRoute) -> list[Segment]:
    """Timeline segments, positioned only from fields the API reports.

    For every stop after the first: driving ends ``wait_minutes`` before the
    reported arrival, waiting fills that gap, and service starts at arrival.
    """
    segments: list[Segment] = []
    for stop in route.stops[1:]:
        drive_start = stop.arrival_minutes - stop.wait_minutes - stop.leg_travel_minutes_from_prev
        if stop.leg_travel_minutes_from_prev > 0:
            segments.append(
                Segment("Drive", drive_start, stop.leg_travel_minutes_from_prev, stop.stop_sequence, stop.node_label)
            )
        if stop.wait_minutes > 0:
            segments.append(
                Segment(
                    "Wait",
                    stop.arrival_minutes - stop.wait_minutes,
                    stop.wait_minutes,
                    stop.stop_sequence,
                    stop.node_label,
                )
            )
        if stop.service_minutes > 0:
            segments.append(
                Segment("Service", stop.arrival_minutes, stop.service_minutes, stop.stop_sequence, stop.node_label)
            )
    return segments


_ACTIVITY_COLORS = {"Drive": common.BLUE, "Service": common.GREEN, "Wait": common.YELLOW}


def build_gantt(route: SolvedRoute) -> go.Figure:
    segments = route_segments(route)
    if not segments:
        return common.empty_figure("This route has no timed activity.", height=200)
    fig = go.Figure()
    row = f"Vehicle {route.vehicle_id}"
    for activity in ("Drive", "Service", "Wait"):
        subset = [s for s in segments if s.activity == activity]
        if not subset:
            continue
        fig.add_trace(
            go.Bar(
                orientation="h",
                y=[row] * len(subset),
                x=[s.duration_min for s in subset],
                base=[s.start_min for s in subset],
                name=activity,
                marker={"color": _ACTIVITY_COLORS[activity], "line": {"width": 1, "color": "#2C3E50"}},
                customdata=[[s.stop_sequence, s.node_label, s.start_min] for s in subset],
                hovertemplate=(
                    f"{activity} at stop %{{customdata[0]}} (%{{customdata[1]}})"
                    "<br>Start: minute %{customdata[2]}<br>Duration: %{x} min<extra></extra>"
                ),
            )
        )
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Minutes from route start", range=[0, max(route.modeled_route_duration, 1)])
    return common.base_layout(fig, f"Timeline of vehicle {route.vehicle_id}", height=240)
