"""Landing page: entry points to the three workflows."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import html

dash.register_page(__name__, path="/", name="Home", title="Vehicle Routing")

layout = dbc.Container(
    [
        html.H1("Vehicle Routing", className="h3 mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H2("1. Upload payload", className="h5"),
                                html.P("Register a VRP payload under a unique process id."),
                                dbc.Button("Open upload", href="/upload", color="primary"),
                            ]
                        )
                    ),
                    md=6,
                    class_name="mb-3",
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H2("2. Batch processing", className="h5"),
                                html.P("Select processes and solve them against the routing service."),
                                dbc.Button("Open batch", href="/batch", color="primary"),
                            ]
                        )
                    ),
                    md=6,
                    class_name="mb-3",
                ),
            ]
        ),
    ],
    fluid=True,
)
