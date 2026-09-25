"""Upload page (Phase 1 placeholder; the upload callback is wired in a later phase)."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(__name__, path="/upload", name="Upload", title="Upload payload")

layout = dbc.Container(
    [
        html.H1("Upload payload", className="h3 mb-3"),
        dbc.Alert(
            "Upload form coming next: process id, JSON payload file, duplicate detection.",
            color="info",
        ),
    ],
    fluid=True,
)
