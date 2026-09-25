"""Upload page: process id + JSON payload file, with duplicate detection."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from vehicle_routing_web.domain.process_id import MAX_PROCESS_ID_LENGTH
from vehicle_routing_web.infrastructure.settings import get_settings
from vehicle_routing_web.presentation.container import get_upload_service
from vehicle_routing_web.presentation.upload_handler import handle_upload

dash.register_page(__name__, path="/upload", name="Upload", title="Upload payload")


def layout() -> dbc.Container:
    return dbc.Container(
        [
            html.H1("Upload payload", className="h3 mb-3"),
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Label("Process id", html_for="upload-process-id"),
                        dbc.Input(
                            id="upload-process-id",
                            type="text",
                            maxLength=MAX_PROCESS_ID_LENGTH,
                            placeholder="e.g. run-2026-09-24",
                            autoComplete="off",
                        ),
                        dbc.FormText(
                            "Unique. Letters, digits, '-' and '_' only; must start with a letter or digit.",
                            class_name="mb-3 d-block",
                        ),
                        dbc.Label("Payload file (JSON)", html_for="upload-file"),
                        dcc.Upload(
                            id="upload-file",
                            children=html.Div(
                                ["Drag and drop a .json file, or ", html.Span("browse", className="text-primary")]
                            ),
                            accept=".json,application/json",
                            max_size=get_settings().max_upload_bytes,
                            multiple=False,
                            className="border border-2 rounded p-4 text-center mb-2",
                            style={"cursor": "pointer"},
                        ),
                        html.Div("No file selected.", id="upload-filename", className="small text-muted mb-3"),
                        dbc.Button("Upload", id="upload-submit", color="primary", n_clicks=0),
                    ]
                ),
                class_name="mb-3",
            ),
            dcc.Loading(html.Div(id="upload-feedback", role="status", **{"aria-live": "polite"}), type="dot"),
        ],
        fluid=True,
    )


@callback(
    Output("upload-filename", "children"),
    Input("upload-file", "filename"),
)
def show_filename(filename: str | None) -> str:
    return f"Selected: {filename}" if filename else "No file selected."


@callback(
    Output("upload-feedback", "children"),
    Input("upload-submit", "n_clicks"),
    State("upload-process-id", "value"),
    State("upload-file", "contents"),
    State("upload-file", "filename"),
    prevent_initial_call=True,
)
def submit_upload(_clicks: int, process_id: str | None, contents: str | None, filename: str | None) -> dbc.Alert:
    outcome = handle_upload(get_upload_service(), process_id, contents, filename)
    children: list = [outcome.message]
    if outcome.success:
        children += [" ", html.A("Go to batch processing", href="/batch", className="alert-link")]
    return dbc.Alert(children, color=outcome.color, dismissable=True)
