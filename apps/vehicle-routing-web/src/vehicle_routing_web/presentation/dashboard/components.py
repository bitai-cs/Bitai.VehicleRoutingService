"""Reusable dashboard building blocks (Bootstrap layout, AG Grid, graphs)."""

from __future__ import annotations

from typing import Any

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from vehicle_routing_web.domain.thresholds import Rating
from vehicle_routing_web.visualization.tables import TableSpec

GRAPH_CONFIG = {"displaylogo": False, "responsive": True}
_BADGE_COLOR = {Rating.GOOD: "success", Rating.WARNING: "warning", Rating.BAD: "danger", Rating.INFO: "secondary"}
_ICON = {Rating.GOOD: "✓", Rating.WARNING: "⚠", Rating.BAD: "✗", Rating.INFO: "i"}


def grid_id(name: str) -> dict[str, str]:
    return {"type": "grid", "name": name}


def csv_button_id(name: str) -> dict[str, str]:
    return {"type": "csv", "name": name}


def rating_badge(rating: Rating, text: str | None = None) -> dbc.Badge:
    """A badge whose text always names the state (icon + words), so colour is never the only cue."""
    return dbc.Badge(f"{_ICON[rating]} {text or rating.label}", color=_BADGE_COLOR[rating], class_name="fs-6")


def not_available(message: str) -> dbc.Alert:
    return dbc.Alert(f"Not available in this solution: {message}", color="secondary", class_name="mb-0 small")


def card(title: str, *children: Any, class_name: str = "h-100") -> dbc.Card:
    return dbc.Card(
        [dbc.CardHeader(html.H3(title, className="h6 mb-0")), dbc.CardBody(list(children))],
        class_name=class_name,
    )


def graph(figure: go.Figure, *, graph_id: str | dict | None = None, label: str = "") -> html.Div:
    component = dcc.Graph(figure=figure, config=GRAPH_CONFIG, **({"id": graph_id} if graph_id else {}))
    return html.Div(component, role="group", **{"aria-label": label} if label else {})


def figure_card(
    title: str, figure: go.Figure, *, graph_id: str | dict | None = None, caption: str | None = None
) -> dbc.Col:
    body: list[Any] = [graph(figure, graph_id=graph_id, label=title)]
    if caption:
        body.append(html.P(caption, className="small text-muted mb-0"))
    return dbc.Col(card(title, *body), lg=6, class_name="mb-3")


def gauge_card(title: str, figure: go.Figure, rating: Rating, status_text: str, description: str) -> dbc.Col:
    return dbc.Col(
        card(
            title,
            graph(figure, label=title),
            html.Div([rating_badge(rating, status_text)], className="mb-2"),
            html.P(description, className="small text-muted mb-0"),
        ),
        lg=6,
        class_name="mb-3",
    )


def with_row_keys(spec: TableSpec) -> list[dict[str, Any]]:
    """Rows plus a string ``row_key`` (AG Grid row ids must be strings; numeric ids would be cast)."""
    return [{**row, "row_key": str(row[spec.row_id])} for row in spec.row_data]


def data_grid(
    name: str,
    spec: TableSpec,
    *,
    page_size: int | None = None,
    single_select: bool = False,
    csv: bool = True,
    fit: bool = False,
) -> html.Div:
    """An AG Grid for ``spec`` with a stable row id, optional pagination and a CSV download button."""
    options: dict[str, Any] = {"domLayout": "autoHeight", "animateRows": False}
    if page_size:
        options.update({"pagination": True, "paginationPageSize": page_size, "paginationPageSizeSelector": False})
    if single_select:
        options["rowSelection"] = {"mode": "singleRow", "checkboxes": False, "enableClickSelection": True}
    grid = dag.AgGrid(
        id=grid_id(name),
        rowData=with_row_keys(spec),
        columnDefs=spec.column_defs,
        getRowId="params.data.row_key",
        rowClassRules=spec.row_class_rules,
        defaultColDef={"sortable": True, "resizable": True},
        dashGridOptions=options,
        columnSize="responsiveSizeToFit" if fit else None,
        csvExportParams={"fileName": f"{name}.csv"},
        # The strings passed to the grid (getRowId, rowClassRules) are constants written in this code base;
        # no user-supplied text is ever placed in a code-evaluated prop.
        dangerously_allow_code=True,
    )
    parts: list[Any] = []
    if csv:
        parts.append(
            dbc.Button(
                "Download CSV", id=csv_button_id(name), size="sm", color="secondary", outline=True, class_name="mb-2"
            )
        )
    if spec.truncated:
        parts.append(
            dbc.Alert(
                "Only the first rows are shown to keep the page responsive.", color="warning", class_name="py-1 small"
            )
        )
    if not spec.row_data:
        parts.append(html.P("No rows to show.", className="small text-muted"))
    parts.append(grid)
    return html.Div(parts)


def metric_list(items: list[tuple[str, str]]) -> dbc.ListGroup:
    return dbc.ListGroup(
        [
            dbc.ListGroupItem(
                [html.Span(label, className="text-muted"), html.Strong(value, className="float-end")],
            )
            for label, value in items
        ],
        flush=True,
    )


def stat_card(label: str, value: str, *, note: str | None = None, badge: dbc.Badge | None = None) -> dbc.Col:
    body: list[Any] = [html.Div(label, className="small text-muted"), html.Div(value, className="h4 mb-1")]
    if badge is not None:
        body.append(badge)
    if note:
        body.append(html.Div(note, className="small text-muted"))
    return dbc.Col(dbc.Card(dbc.CardBody(body), class_name="h-100"), xs=6, md=4, xl=3, class_name="mb-3")
