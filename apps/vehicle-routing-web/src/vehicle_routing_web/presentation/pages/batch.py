"""Batch processing page: pick processes in an AG Grid and solve them in parallel."""

from __future__ import annotations

from typing import Any

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from vehicle_routing_web.presentation.batch_view import (
    COLUMN_DEFS,
    GRID_OPTIONS,
    build_rows,
    describe_submission,
    selected_ids,
)
from vehicle_routing_web.presentation.container import get_batch_runner, get_repository

dash.register_page(__name__, path="/batch", name="Batch processing", title="Batch processing")

REFRESH_INTERVAL_MS = 3000


def layout() -> dbc.Container:
    return dbc.Container(
        [
            html.H1("Batch processing", className="h3 mb-3"),
            dbc.Card(
                dbc.CardBody(
                    dbc.Stack(
                        [
                            dbc.Button("Solve selected", id="batch-solve", color="primary", n_clicks=0),
                            dbc.Button("Refresh", id="batch-refresh", color="secondary", outline=True, n_clicks=0),
                            dbc.Button(
                                "Open dashboard",
                                id="batch-open-dashboard",
                                color="success",
                                outline=True,
                                disabled=True,
                            ),
                            html.Span(
                                "Select rows, then Solve. Open dashboard needs exactly one solved row.",
                                className="small text-muted",
                            ),
                        ],
                        direction="horizontal",
                        gap=2,
                        class_name="flex-wrap",
                    )
                ),
                class_name="mb-3",
            ),
            html.Div(id="batch-feedback", role="status"),
            dag.AgGrid(
                id="process-grid",
                rowData=build_rows(get_repository(), get_batch_runner().active_ids()),
                columnDefs=COLUMN_DEFS,
                getRowId="params.data.process_id",
                dashGridOptions=GRID_OPTIONS,
                defaultColDef={"sortable": True, "resizable": True},
                # Constant strings only (getRowId, cellClassRules); row text is data, never code.
                dangerously_allow_code=True,
                style={"height": "480px"},
            ),
            dcc.Interval(id="batch-interval", interval=REFRESH_INTERVAL_MS),
            dcc.Store(id="batch-trigger"),
        ],
        fluid=True,
    )


@callback(
    Output("process-grid", "rowData"),
    Input("batch-interval", "n_intervals"),
    Input("batch-refresh", "n_clicks"),
    Input("batch-trigger", "data"),
    State("process-grid", "rowData"),
)
def refresh_grid(_ticks: int, _clicks: int, _trigger: Any, current: list[dict] | None) -> Any:
    rows = build_rows(get_repository(), get_batch_runner().active_ids())
    return no_update if rows == current else rows


@callback(
    Output("batch-feedback", "children"),
    Output("batch-trigger", "data"),
    Input("batch-solve", "n_clicks"),
    State("process-grid", "selectedRows"),
    prevent_initial_call=True,
)
def solve_selected(_clicks: int, selected: list[dict] | None) -> tuple[Any, Any]:
    ids = selected_ids(selected)
    if not ids:
        return dbc.Alert("Select at least one process first.", color="warning", dismissable=True), no_update
    submission, _futures = get_batch_runner().submit(ids)
    color, message = describe_submission(submission)
    return dbc.Alert(message, color=color, dismissable=True), {"submitted": list(submission.started)}


@callback(
    Output("batch-open-dashboard", "href"),
    Output("batch-open-dashboard", "disabled"),
    Input("process-grid", "selectedRows"),
)
def update_dashboard_link(selected: list[dict] | None) -> tuple[Any, bool]:
    rows = selected or []
    if len(rows) == 1 and rows[0].get("status") == "solved":
        return f"/dashboard/{rows[0]['process_id']}", False
    return None, True
