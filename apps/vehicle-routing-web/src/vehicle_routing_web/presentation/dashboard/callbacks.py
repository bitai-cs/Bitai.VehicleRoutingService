"""Thin dashboard callbacks: validate input, load the cached solution, delegate to builders."""

from __future__ import annotations

import logging
from typing import Any

import dash_bootstrap_components as dbc
from dash import MATCH, Input, Output, State, callback, no_update

from vehicle_routing_web.domain.artifacts import ProcessStatus
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, StorageCorruptedError
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.presentation.container import get_solution_service
from vehicle_routing_web.presentation.dashboard import components as c
from vehicle_routing_web.presentation.dashboard import tabs
from vehicle_routing_web.visualization import geography

logger = logging.getLogger(__name__)

TABS_ID = "dash-tabs"
CONTENT_ID = "dash-tab-content"
CONTEXT_ID = "dash-context"
SELECTION_ID = "dash-selection"


def load_solution(context: dict[str, Any] | None) -> tuple[Solution | None, Any]:
    """Return ``(solution, None)`` or ``(None, alert)``. Store contents come from the browser, so re-validate."""
    process_id = (context or {}).get("process_id")
    if not isinstance(process_id, str):
        return None, dbc.Alert("No process selected.", color="warning")
    try:
        loaded = get_solution_service().load(process_id)
    except InvalidProcessIdError, ProcessNotFoundError:
        return None, dbc.Alert("Process not found.", color="warning")
    except StorageCorruptedError:
        logger.exception("Stored solution for %s could not be loaded", process_id)
        return None, dbc.Alert("The stored solution could not be read.", color="danger")
    if loaded.solution is None:
        state = "still running" if loaded.status is ProcessStatus.RUNNING else "no longer available"
        return None, dbc.Alert(f"The solution is {state}. Reload the page.", color="info")
    return loaded.solution, None


def _selected_vehicle(solution: Solution, value: str | None) -> int | None:
    vehicle = tabs.parse_vehicle(value)
    return vehicle if vehicle in solution.routes_by_vehicle else None


@callback(
    Output(CONTENT_ID, "children"),
    Input(TABS_ID, "active_tab"),
    State(CONTEXT_ID, "data"),
    State(SELECTION_ID, "data"),
)
def render_tab(active_tab: str, context: dict | None, selection: dict | None) -> Any:
    solution, alert = load_solution(context)
    if solution is None:
        return alert
    vehicle = _selected_vehicle(solution, tabs.vehicle_value((selection or {}).get("vehicle")))
    return tabs.build_tab(active_tab, solution, vehicle)


@callback(
    Output(tabs.GEO_MAP, "figure"),
    Output(tabs.GEO_DETAIL, "children"),
    Output(tabs.GEO_OPEN_STOPS, "disabled"),
    Output(SELECTION_ID, "data", allow_duplicate=True),
    Input(tabs.GEO_VEHICLE_SELECT, "value"),
    State(CONTEXT_ID, "data"),
    prevent_initial_call=True,
)
def select_geography_vehicle(value: str | None, context: dict | None) -> tuple[Any, Any, bool, Any]:
    solution, _ = load_solution(context)
    if solution is None:
        return no_update, no_update, True, no_update
    vehicle = _selected_vehicle(solution, value)
    return (
        geography.build_route_map(solution, vehicle),
        tabs.vehicle_detail(solution, vehicle),
        vehicle is None,
        {"vehicle": vehicle},
    )


@callback(
    Output(TABS_ID, "active_tab", allow_duplicate=True),
    Input(tabs.GEO_OPEN_STOPS, "n_clicks"),
    prevent_initial_call=True,
)
def open_stops_tab(clicks: int | None) -> Any:
    # Dash also fires this when the button is first rendered (n_clicks is None): only react to real clicks.
    return tabs.TAB_STOPS if clicks else no_update


@callback(
    Output(tabs.STOPS_GANTT, "children"),
    Output("stops-table-host", "children"),
    Output(SELECTION_ID, "data", allow_duplicate=True),
    Input(tabs.STOPS_VEHICLE_SELECT, "value"),
    State(CONTEXT_ID, "data"),
    prevent_initial_call=True,
)
def select_stops_vehicle(value: str | None, context: dict | None) -> tuple[Any, Any, Any]:
    solution, _ = load_solution(context)
    if solution is None:
        return no_update, no_update, no_update
    vehicle = _selected_vehicle(solution, value)
    gantt, table = tabs.stops_body(solution, vehicle)
    return gantt, table, {"vehicle": vehicle}


@callback(
    Output(c.grid_id(tabs.GRID_OMITTED), "selectedRows"),
    Input(tabs.COVERAGE_OMITTED_MAP, "clickData"),
    prevent_initial_call=True,
)
def highlight_omitted_row(click_data: dict | None) -> Any:
    points = (click_data or {}).get("points") or []
    custom = points[0].get("customdata") if points else None
    if not custom or not isinstance(custom[0], int):
        return no_update
    return [{"row_key": str(custom[0])}]


@callback(
    Output({"type": "grid", "name": MATCH}, "exportDataAsCsv"),
    Input({"type": "csv", "name": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def export_grid_csv(clicks: int | None) -> Any:
    return True if clicks else no_update
