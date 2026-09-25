"""Dashboard page for one process: loading/in-progress/failed/error states, or the full tabbed dashboard."""

from __future__ import annotations

import logging
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from vehicle_routing_web.domain.artifacts import ProcessStatus
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, StorageCorruptedError
from vehicle_routing_web.domain.process_id import validate_process_id
from vehicle_routing_web.presentation.container import get_solution_service
from vehicle_routing_web.presentation.dashboard import callbacks  # noqa: F401  (registers the dashboard callbacks)
from vehicle_routing_web.presentation.dashboard.header import build_executive_summary, build_header
from vehicle_routing_web.presentation.dashboard.tabs import TAB_GEOGRAPHY, TAB_LABELS

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path_template="/dashboard/<process_id>",
    name="Dashboard",
    title="Solution dashboard",
)


def _page(*children: Any) -> dbc.Container:
    return dbc.Container(list(children), fluid=True)


def layout(process_id: str | None = None, **_: Any) -> dbc.Container:
    try:
        valid_id = validate_process_id(process_id)
    except InvalidProcessIdError:
        return _page(dbc.Alert("Invalid process id in the address.", color="danger"))

    title = html.H1(f"Dashboard: {valid_id}", className="h3 mb-3")
    try:
        loaded = get_solution_service().load(valid_id)
    except ProcessNotFoundError:
        return _page(dbc.Alert("Process not found.", color="warning"), dbc.Button("Batch processing", href="/batch"))
    except StorageCorruptedError:
        logger.exception("Unreadable stored outcome for %s", valid_id)
        return _page(title, dbc.Alert("The stored result could not be read.", color="danger"))

    if loaded.status is ProcessStatus.FAILED:
        error = loaded.error or {}
        return _page(
            title,
            dbc.Alert(
                f"Solving failed: {error.get('message', 'unknown error')} "
                f"(type: {error.get('error_type', 'unknown')}, at {error.get('occurred_at', 'unknown time')}).",
                color="danger",
            ),
            dbc.Button("Back to batch processing", href="/batch", color="secondary"),
        )
    if loaded.solution is None:
        text = (
            "Solving is in progress. Reload this page when it finishes."
            if loaded.status is ProcessStatus.RUNNING
            else "This process has not been solved yet."
        )
        return _page(
            title, dbc.Alert(text, color="info"), dbc.Button("Go to batch processing", href="/batch", color="primary")
        )

    solution = loaded.solution
    return _page(
        dcc.Store(id="dash-context", data={"process_id": valid_id}),
        dcc.Store(id="dash-selection", data={"vehicle": None}),
        build_header(solution),
        build_executive_summary(solution),
        dbc.Tabs(
            [dbc.Tab(label=label, tab_id=tab_id) for tab_id, label in TAB_LABELS],
            id="dash-tabs",
            active_tab=TAB_GEOGRAPHY,
            class_name="mb-3",
        ),
        dcc.Loading(html.Div(id="dash-tab-content"), type="dot"),
    )
