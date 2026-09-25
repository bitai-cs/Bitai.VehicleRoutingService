"""Geographic overview: planar x/y route map (equal aspect) and the vehicle detail rows.

The payload coordinates are planar (km in the reference scenario), not
latitude/longitude, so this is a Plotly scatter with a 1:1 aspect ratio rather
than a tiled map.
"""

from __future__ import annotations

import plotly.graph_objects as go

from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.domain.solve_response import SolvedRoute
from vehicle_routing_web.visualization import common

_DASH = {(True, True): "solid", (True, False): "dash", (False, True): "dash", (False, False): "dot"}
DIMMED_OPACITY = 0.1
LEG_STYLE_NOTE = (
    "Line style of first/last legs: solid = cost and time counted, dashed = only one of them counted, "
    "dotted = neither counted. Middle legs are always solid."
)


def _route_points(solution: Solution, route: SolvedRoute) -> tuple[list[float], list[float], list[str], list[str]]:
    xs: list[float] = []
    ys: list[float] = []
    hover: list[str] = []
    order: list[str] = []
    for stop in route.stops:
        x, y = solution.scenario.coord(stop.node_id)
        xs.append(x)
        ys.append(y)
        hover.append(f"Node {stop.node_id}: {stop.node_label}<br>Arrival: {stop.arrival_time}")
        order.append(str(stop.stop_sequence))
    return xs, ys, hover, order


def _leg_traces(
    solution: Solution, route: SolvedRoute, xs: list[float], ys: list[float], opacity: float
) -> list[go.Scatter]:
    n = len(xs)
    if n < 2:
        return []
    color = common.route_color(route.vehicle_id)
    first_dash = _DASH[solution.scenario.leg_counted(route.vehicle_id, first=True)]
    last_dash = _DASH[solution.scenario.leg_counted(route.vehicle_id, first=False)]
    groups = [(first_dash, [(0, 1)])]
    if n > 3:
        groups.append(("solid", [(i, i + 1) for i in range(1, n - 2)]))
    if n > 2:
        groups.append((last_dash, [(n - 2, n - 1)]))
    traces = []
    for dash, segments in groups:
        lx: list[float | None] = []
        ly: list[float | None] = []
        for a, b in segments:
            lx += [xs[a], xs[b], None]
            ly += [ys[a], ys[b], None]
        traces.append(
            go.Scatter(
                x=lx,
                y=ly,
                mode="lines",
                line={"color": color, "width": 2, "dash": dash},
                opacity=opacity,
                hoverinfo="skip",
                showlegend=False,
                legendgroup=f"v{route.vehicle_id}",
            )
        )
    return traces


def build_route_map(solution: Solution, selected_vehicle: int | None = None) -> go.Figure:
    scenario = solution.scenario
    omitted_ids = {e.node_id for e in solution.omitted_employees}
    fig = go.Figure()

    served_ids = [n for n in scenario.employee_node_ids if n not in omitted_ids]
    fig.add_trace(
        go.Scatter(
            x=[scenario.coord(n)[0] for n in served_ids],
            y=[scenario.coord(n)[1] for n in served_ids],
            mode="markers+text",
            text=[scenario.label(n) for n in served_ids],
            textposition="bottom center",
            textfont={"size": 9, "color": "#566573"},
            marker={"symbol": "circle", "size": 7, "color": common.GRAY},
            customdata=[[n, scenario.label(n), scenario.priority(n)] for n in served_ids],
            hovertemplate=(
                "Employee %{customdata[1]} (node %{customdata[0]})<br>Priority: %{customdata[2]}<extra></extra>"
            ),
            name="Employees (served)",
        )
    )
    if solution.omitted_employees:
        fig.add_trace(
            go.Scatter(
                x=[e.x for e in solution.omitted_employees],
                y=[e.y for e in solution.omitted_employees],
                mode="markers",
                marker={"symbol": "x", "size": 11, "color": common.RED, "line": {"width": 2, "color": common.RED}},
                customdata=[[e.node_id, e.label, e.priority] for e in solution.omitted_employees],
                hovertemplate=(
                    "OMITTED %{customdata[1]} (node %{customdata[0]})<br>Priority: %{customdata[2]}<extra></extra>"
                ),
                name="Omitted employees",
            )
        )
    for ids, symbol, name in (
        (sorted(set(scenario.vehicle_start_nodes)), "diamond", "Route start"),
        (sorted(set(scenario.vehicle_end_nodes)), "square", "Route end"),
    ):
        fig.add_trace(
            go.Scatter(
                x=[scenario.coord(n)[0] for n in ids],
                y=[scenario.coord(n)[1] for n in ids],
                mode="markers+text",
                text=[scenario.label(n) for n in ids],
                textposition="top center",
                textfont={"size": 9},
                marker={"symbol": symbol, "size": 10, "color": "#FFFFFF", "line": {"width": 2, "color": "#2C3E50"}},
                customdata=[[n, scenario.label(n)] for n in ids],
                hovertemplate=f"{name} %{{customdata[1]}} (node %{{customdata[0]}})<extra></extra>",
                name=name,
            )
        )

    for route in solution.active_routes:
        opacity = 1.0 if selected_vehicle in (None, route.vehicle_id) else DIMMED_OPACITY
        xs, ys, hover, order = _route_points(solution, route)
        for trace in _leg_traces(solution, route, xs, ys, opacity):
            fig.add_trace(trace)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=order,
                textposition="top right",
                textfont={"size": 10},
                marker={"size": 6, "color": common.route_color(route.vehicle_id)},
                opacity=opacity,
                hovertext=hover,
                hoverinfo="text",
                name=f"Vehicle {route.vehicle_id}",
                legendgroup=f"v{route.vehicle_id}",
            )
        )

    fig.update_xaxes(title_text="x (km)", showgrid=True, zeroline=False)
    fig.update_yaxes(title_text="y (km)", showgrid=True, zeroline=False, scaleanchor="x", scaleratio=1)
    common.base_layout(fig, "Routes", height=680)
    fig.update_layout(
        legend={"orientation": "v", "x": 1.01, "y": 1},
        margin={"l": 55, "r": 150, "t": 50, "b": 50},
        uirevision=solution.process_id,
    )
    return fig


def vehicle_detail_rows(route: SolvedRoute) -> list[tuple[str, str]]:
    """Label/value pairs for the vehicle detail panel."""
    return [
        ("Vehicle ID", str(route.vehicle_id)),
        ("Route", f"{route.start_node_label} → {route.end_node_label}"),
        ("Employees served", str(route.covered_demand)),
        ("Total duration", f"{route.modeled_route_duration} min"),
        ("Physical distance", f"{route.physical_route_distance:.3f} km"),
        ("Capacity utilization", f"{route.demand_utilization_pct:.1f} %"),
        ("Departure time", route.departure_time),
        ("Arrival time", route.arrival_time),
        ("Time remaining to limit", f"{route.remaining_time_to_limit_min} min"),
    ]
