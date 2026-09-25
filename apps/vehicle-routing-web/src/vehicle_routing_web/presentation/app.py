"""Dash application factory."""

from __future__ import annotations

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

from vehicle_routing_web.presentation.components.navbar import build_navbar

PAGES_FOLDER = Path(__file__).parent / "pages"


def create_app() -> Dash:
    app = Dash(
        __name__,
        use_pages=True,
        pages_folder=str(PAGES_FOLDER),
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        title="Vehicle Routing",
        suppress_callback_exceptions=True,
    )
    app.layout = html.Div([build_navbar(), dash.page_container])
    return app
