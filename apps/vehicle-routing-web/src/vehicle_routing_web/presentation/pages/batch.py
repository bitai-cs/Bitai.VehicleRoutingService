"""Batch processing page (Phase 1 placeholder; AG Grid process list arrives with batch processing)."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(__name__, path="/batch", name="Batch processing", title="Batch processing")

layout = dbc.Container(
    [
        html.H1("Batch processing", className="h3 mb-3"),
        dbc.Alert(
            "Process list (AG Grid, multi-select) and solve controls coming in the batch phase.",
            color="info",
        ),
    ],
    fluid=True,
)
