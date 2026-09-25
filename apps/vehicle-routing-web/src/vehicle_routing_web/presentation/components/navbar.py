"""Top navigation bar shared by every page."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

NAV_LINKS: tuple[tuple[str, str], ...] = (
    ("Upload", "/upload"),
    ("Batch processing", "/batch"),
)


def build_navbar() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("Vehicle Routing", href="/", class_name="fw-semibold"),
                dbc.Nav(
                    [dbc.NavItem(dbc.NavLink(label, href=href, active="exact")) for label, href in NAV_LINKS],
                    navbar=True,
                    class_name="me-auto",
                ),
                html.Span("Solution dashboard", className="navbar-text small"),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        class_name="mb-4",
    )
