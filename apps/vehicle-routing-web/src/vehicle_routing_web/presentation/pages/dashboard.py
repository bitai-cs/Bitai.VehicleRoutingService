"""Dashboard page for one process (Phase 1 placeholder)."""

from __future__ import annotations

from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import html

from vehicle_routing_web.domain.exceptions import InvalidProcessIdError
from vehicle_routing_web.domain.process_id import validate_process_id

dash.register_page(
    __name__,
    path_template="/dashboard/<process_id>",
    name="Dashboard",
    title="Solution dashboard",
)


def layout(process_id: str | None = None, **_: Any) -> dbc.Container:
    try:
        valid_id = validate_process_id(process_id)
    except InvalidProcessIdError:
        return dbc.Container(
            dbc.Alert("Invalid process id in the address.", color="danger"),
            fluid=True,
        )
    return dbc.Container(
        [
            html.H1(f"Dashboard: {valid_id}", className="h3 mb-3"),
            dbc.Alert(
                "Dashboard tabs (see DASHBOARD_SPECIFICATION.md) will be built from solve-result.json.",
                color="info",
            ),
        ],
        fluid=True,
    )
