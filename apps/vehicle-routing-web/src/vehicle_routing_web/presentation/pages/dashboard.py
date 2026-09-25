"""Dashboard page for one process.

Phase 2 scope: loads the process outcome from disk (same file constants as the
batch runner) and shows headline numbers; the full tab set from
DASHBOARD_SPECIFICATION.md comes in a later phase.
"""

from __future__ import annotations

import logging
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import html

from vehicle_routing_web.domain.artifacts import ProcessStatus
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, StorageCorruptedError
from vehicle_routing_web.domain.process_id import validate_process_id
from vehicle_routing_web.presentation.container import get_repository

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path_template="/dashboard/<process_id>",
    name="Dashboard",
    title="Solution dashboard",
)


def _page(*children: Any) -> dbc.Container:
    return dbc.Container(list(children), fluid=True)


def _kpi(label: str, value: str) -> dbc.Col:
    return dbc.Col(
        dbc.Card(dbc.CardBody([html.Div(label, className="small text-muted"), html.Div(value, className="h4 mb-0")])),
        sm=6,
        lg=3,
        class_name="mb-3",
    )


def layout(process_id: str | None = None, **_: Any) -> dbc.Container:
    try:
        valid_id = validate_process_id(process_id)
    except InvalidProcessIdError:
        return _page(dbc.Alert("Invalid process id in the address.", color="danger"))

    title = html.H1(f"Dashboard: {valid_id}", className="h3 mb-3")
    repo = get_repository()
    try:
        status = repo.get_status(valid_id)
        if status is ProcessStatus.SOLVED:
            result = repo.read_result(valid_id)
        elif status is ProcessStatus.FAILED:
            error = repo.read_error(valid_id) or {}
            return _page(
                title,
                dbc.Alert(
                    f"Solving failed: {error.get('message', 'unknown error')} "
                    f"(type: {error.get('error_type', 'unknown')}, at {error.get('occurred_at', 'unknown time')}).",
                    color="danger",
                ),
                dbc.Button("Back to batch processing", href="/batch", color="secondary"),
            )
        else:
            text = (
                "Solving is in progress."
                if status is ProcessStatus.RUNNING
                else "This process has not been solved yet."
            )
            return _page(
                title,
                dbc.Alert(text, color="info"),
                dbc.Button("Go to batch processing", href="/batch", color="primary"),
            )
    except ProcessNotFoundError:
        return _page(dbc.Alert("Process not found.", color="warning"))
    except StorageCorruptedError:
        logger.exception("Unreadable stored outcome for %s", valid_id)
        return _page(title, dbc.Alert("The stored result could not be read.", color="danger"))

    if result is None:  # status changed between the two disk reads
        return _page(title, dbc.Alert("The result is no longer available.", color="warning"))
    return _page(
        title,
        dbc.Row(
            [
                _kpi("Solver status", result.status),
                _kpi("Service level", f"{result.service_level_pct:.1f} %"),
                _kpi("Search time", f"{result.search_wall_time_ms} ms"),
                _kpi("Objective value", str(result.total_objective_value)),
            ]
        ),
        dbc.Alert(
            "Full dashboard tabs (see DASHBOARD_SPECIFICATION.md) come in a later phase.",
            color="info",
        ),
    )
