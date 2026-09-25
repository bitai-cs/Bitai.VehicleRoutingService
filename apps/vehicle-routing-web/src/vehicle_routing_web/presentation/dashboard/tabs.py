"""Tab content builders: compose figure/table builders into Bootstrap layouts."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.domain.kpi_table import SECTION_TITLES
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.presentation.dashboard import components as c
from vehicle_routing_web.visualization import balance, coverage, efficiency, gauges, geography, objective, stops, tables

TAB_GEOGRAPHY = "tab-geography"
TAB_COVERAGE = "tab-coverage"
TAB_EFFICIENCY = "tab-efficiency"
TAB_BALANCE = "tab-balance"
TAB_STOPS = "tab-stops"
TAB_OBJECTIVE = "tab-objective"
TAB_SUSTAINABILITY = "tab-sustainability"
TAB_SUMMARY = "tab-summary"

TAB_LABELS: tuple[tuple[str, str], ...] = (
    (TAB_GEOGRAPHY, "Geography"),
    (TAB_COVERAGE, "Coverage"),
    (TAB_EFFICIENCY, "Efficiency"),
    (TAB_BALANCE, "Load balance"),
    (TAB_STOPS, "Stops"),
    (TAB_OBJECTIVE, "Objective"),
    (TAB_SUSTAINABILITY, "Sustainability"),
    (TAB_SUMMARY, "Summary"),
)

ALL_VEHICLES = "all"

GEO_VEHICLE_SELECT = "geo-vehicle"
GEO_MAP = "geo-map"
GEO_DETAIL = "geo-detail"
GEO_OPEN_STOPS = "geo-open-stops"
STOPS_VEHICLE_SELECT = "stops-vehicle"
STOPS_GANTT = "stops-gantt"
COVERAGE_OMITTED_MAP = "coverage-omitted-map"
GRID_OMITTED = "omitted"
GRID_ROUTES = "routes"
GRID_STOPS = "stops"


def vehicle_options(solution: Solution, *, all_label: str) -> list[dict[str, str]]:
    return [{"label": all_label, "value": ALL_VEHICLES}] + [
        {"label": f"Vehicle {r.vehicle_id} ({r.start_node_label} → {r.end_node_label})", "value": str(r.vehicle_id)}
        for r in sorted(solution.active_routes, key=lambda r: r.vehicle_id)
    ]


def vehicle_value(vehicle: int | None) -> str:
    return ALL_VEHICLES if vehicle is None else str(vehicle)


def parse_vehicle(value: str | None) -> int | None:
    if value in (None, ALL_VEHICLES, ""):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def build_tab(tab_id: str, solution: Solution, vehicle: int | None) -> Any:
    builders = {
        TAB_GEOGRAPHY: lambda: geography_tab(solution, vehicle),
        TAB_COVERAGE: lambda: coverage_tab(solution),
        TAB_EFFICIENCY: lambda: efficiency_tab(solution),
        TAB_BALANCE: lambda: balance_tab(solution),
        TAB_STOPS: lambda: stops_tab(solution, vehicle),
        TAB_OBJECTIVE: lambda: objective_tab(solution),
        TAB_SUSTAINABILITY: lambda: sustainability_tab(solution),
        TAB_SUMMARY: lambda: summary_tab(solution),
    }
    builder = builders.get(tab_id)
    if builder is None:
        return dbc.Alert("Unknown tab.", color="warning")
    return builder()


# --- Geography ---------------------------------------------------------------


def vehicle_detail(solution: Solution, vehicle: int | None) -> Any:
    if vehicle is None or vehicle not in solution.routes_by_vehicle:
        return html.P("Select a vehicle to see its details.", className="text-muted mb-0")
    return c.metric_list(geography.vehicle_detail_rows(solution.routes_by_vehicle[vehicle]))


def geography_tab(solution: Solution, vehicle: int | None) -> Any:
    return dbc.Row(
        [
            dbc.Col(
                c.card(
                    "Route map",
                    c.graph(geography.build_route_map(solution, vehicle), graph_id=GEO_MAP, label="Route map"),
                    html.P(geography.LEG_STYLE_NOTE, className="small text-muted mb-0"),
                ),
                lg=7,
                class_name="mb-3",
            ),
            dbc.Col(
                [
                    c.card(
                        "Vehicle",
                        dbc.Label("Show route", html_for=GEO_VEHICLE_SELECT),
                        dbc.Select(
                            id=GEO_VEHICLE_SELECT,
                            options=vehicle_options(solution, all_label="All routes"),
                            value=vehicle_value(vehicle),
                            class_name="mb-3",
                        ),
                        html.Div(vehicle_detail(solution, vehicle), id=GEO_DETAIL),
                        dbc.Button(
                            "View this vehicle's stops",
                            id=GEO_OPEN_STOPS,
                            color="primary",
                            outline=True,
                            disabled=vehicle is None,
                            class_name="mt-3",
                        ),
                    )
                ],
                lg=5,
                class_name="mb-3",
            ),
        ]
    )


# --- Coverage ----------------------------------------------------------------


def coverage_tab(solution: Solution) -> Any:
    r = solution.response
    sl_bands = gauges.SERVICE_LEVEL_BANDS
    return html.Div(
        [
            dbc.Row(
                [
                    c.figure_card("Coverage", coverage.build_coverage_donut(solution)),
                    c.figure_card("Omitted employees by priority", coverage.build_omitted_by_priority(solution)),
                    c.gauge_card(
                        "Service level",
                        gauges.build_gauge(
                            r.service_level_pct, "Service level", sl_bands, target=t.SERVICE_LEVEL_TARGET, suffix="%"
                        ),
                        gauges.band_rating(r.service_level_pct, sl_bands),
                        gauges.band_label(r.service_level_pct, sl_bands),
                        "Share of employees served relative to total demand.",
                    ),
                    c.gauge_card(
                        "Weighted service level",
                        gauges.build_gauge(
                            r.weighted_service_level_pct,
                            "Weighted service level",
                            sl_bands,
                            target=t.WEIGHTED_SERVICE_LEVEL_TARGET,
                            suffix="%",
                        ),
                        gauges.band_rating(r.weighted_service_level_pct, sl_bands),
                        gauges.band_label(r.weighted_service_level_pct, sl_bands),
                        "Priority-weighted service coverage.",
                    ),
                    c.figure_card(
                        "Omitted employees by location",
                        coverage.build_omitted_map(solution),
                        graph_id=COVERAGE_OMITTED_MAP,
                        caption="Click a point to select it in the table. Marker size by distance to a reference "
                        "depot is not shown: the reference location is not part of the solution data.",
                    ),
                    dbc.Col(
                        c.card(
                            "Omitted employees",
                            c.data_grid(
                                GRID_OMITTED, tables.omitted_table(solution), page_size=20, single_select=True, fit=True
                            ),
                        ),
                        lg=6,
                        class_name="mb-3",
                    ),
                ]
            )
        ]
    )


# --- Efficiency --------------------------------------------------------------


def efficiency_tab(solution: Solution) -> Any:
    r = solution.response
    return dbc.Row(
        [
            c.figure_card("Route duration distribution", efficiency.build_duration_distribution(solution)),
            c.figure_card("Route distance distribution", efficiency.build_distance_distribution(solution)),
            c.figure_card(
                "Demand utilization vs. duration",
                efficiency.build_utilization_vs_duration(solution),
                caption="Marker size grows with the number of service stops.",
            ),
            c.figure_card(
                "Time composition by route",
                efficiency.build_time_composition(solution),
                caption="Slack is route duration not explained by drive, service or wait time.",
            ),
            c.gauge_card(
                "Fleet utilization",
                gauges.build_gauge(
                    r.fleet_utilization_pct, "Fleet utilization", gauges.FLEET_UTILIZATION_BANDS, suffix="%"
                ),
                gauges.band_rating(r.fleet_utilization_pct, gauges.FLEET_UTILIZATION_BANDS),
                gauges.band_label(r.fleet_utilization_pct, gauges.FLEET_UTILIZATION_BANDS),
                f"{solution.metrics.routes_active} of {solution.metrics.routes_total} vehicles used. "
                "Green band 60-90% is the preferred range.",
            ),
            dbc.Col(
                c.card(
                    "Routes summary",
                    c.data_grid(GRID_ROUTES, tables.routes_table(solution), page_size=15, fit=True),
                    html.P(
                        "Per-route service level is not available: the solution does not report demand per route.",
                        className="small text-muted mt-2 mb-0",
                    ),
                ),
                lg=6,
                class_name="mb-3",
            ),
        ]
    )


# --- Load balance ------------------------------------------------------------


def _cv_gauge_card(title: str, value: float, description: str) -> Any:
    axis_max = gauges.cv_axis_max(value)
    bands = gauges.cv_bands(axis_max)
    fig = gauges.build_gauge(value, title, bands, target=t.CV_TARGET_MAX, decimals=6)
    return c.gauge_card(title, fig, gauges.band_rating(value, bands), gauges.band_label(value, bands), description)


def balance_tab(solution: Solution) -> Any:
    m = solution.metrics
    stats = balance.balance_stats(solution)
    return dbc.Row(
        [
            _cv_gauge_card(
                "Duration balance (CV)",
                m.duration_balance_cv,
                "Lower values mean more balanced route times. Preferred: 0.50 or less.",
            ),
            _cv_gauge_card(
                "Service stops balance (CV)",
                m.service_stops_balance_cv,
                "Lower values mean a more uniform stop distribution. Preferred: 0.50 or less.",
            ),
            c.figure_card(
                "Workload balance",
                balance.build_std_bars(solution),
                caption="Lower values indicate more balanced fleet operations. Bars use different units.",
            ),
            dbc.Col(
                c.card(
                    "Route comparison", c.graph(balance.build_route_heatmap(solution), label="Route performance matrix")
                ),
                lg=6,
                class_name="mb-3",
            ),
            c.figure_card("Duration vs. demand", balance.build_duration_vs_demand(solution)),
            dbc.Col(
                c.card(
                    "Balance summary",
                    c.metric_list([(label, value) for label, value, _ in stats]),
                    html.Div(
                        [
                            html.Div([label, ": ", c.rating_badge(rating)], className="small mt-1")
                            for label, _, rating in stats
                            if rating is not t.Rating.INFO
                        ],
                        className="mt-2",
                    ),
                ),
                lg=6,
                class_name="mb-3",
            ),
        ]
    )


# --- Stops -------------------------------------------------------------------


def stops_body(solution: Solution, vehicle: int | None) -> tuple[Any, Any]:
    """The (gantt, table) content for a vehicle selection; also used by the callback."""
    route = solution.routes_by_vehicle.get(vehicle) if vehicle is not None else None
    gantt: Any = (
        c.graph(stops.build_gantt(route), label="Route timeline")
        if route is not None
        else html.P("Select a single vehicle to see its timeline.", className="text-muted mb-0")
    )
    return gantt, c.data_grid(GRID_STOPS, tables.stops_table(solution, vehicle), page_size=20)


def stops_tab(solution: Solution, vehicle: int | None) -> Any:
    gantt, table = stops_body(solution, vehicle)
    return html.Div(
        [
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Label("Vehicle", html_for=STOPS_VEHICLE_SELECT),
                        dbc.Select(
                            id=STOPS_VEHICLE_SELECT,
                            options=vehicle_options(solution, all_label="All stops (aggregated)"),
                            value=vehicle_value(vehicle),
                        ),
                    ],
                    md=6,
                    lg=4,
                ),
                class_name="mb-3",
            ),
            html.Div(c.card("Timeline", html.Div(gantt, id=STOPS_GANTT)), className="mb-3"),
            c.card("Stops", html.Div(table, id="stops-table-host"), class_name="mb-3"),
        ]
    )


# --- Objective ---------------------------------------------------------------

_ALERT_COLOR = {t.Rating.BAD: "danger", t.Rating.WARNING: "warning", t.Rating.INFO: "info", t.Rating.GOOD: "success"}


def objective_tab(solution: Solution) -> Any:
    r = solution.response
    alerts = [
        dbc.Alert(
            [c.rating_badge(a.level, a.level.label), " ", a.message],
            color=_ALERT_COLOR[a.level],
            class_name="py-2 mb-2",
        )
        for a in objective.objective_alerts(solution)
    ]
    return dbc.Row(
        [
            dbc.Col(
                c.card(
                    "Objective decomposition",
                    c.graph(objective.build_objective_donut(solution), label="Objective decomposition"),
                ),
                lg=6,
                class_name="mb-3",
            ),
            dbc.Col(
                c.card(
                    "Objective metrics",
                    c.metric_list(
                        [
                            ("Travel cost", f"{r.objective_travel_cost:,}"),
                            ("Omission penalty", f"{r.objective_omission_penalty:,}"),
                            ("Unattributed cost", f"{r.objective_unattributed_cost:,}"),
                            ("Total objective value", f"{r.total_objective_value:,}"),
                            ("Search time", f"{r.search_wall_time_ms:,} ms"),
                        ]
                    ),
                ),
                lg=6,
                class_name="mb-3",
            ),
            dbc.Col(
                c.card(
                    "Solver statistics",
                    c.metric_list(
                        [
                            ("Branches", f"{r.solver_branches:,}"),
                            ("Failures", f"{r.solver_failures:,}"),
                            ("Status", r.status),
                            ("Status detail", r.solver_status_detail),
                        ]
                    ),
                ),
                lg=6,
                class_name="mb-3",
            ),
            dbc.Col(c.card("Validation alerts", *alerts), lg=6, class_name="mb-3"),
        ]
    )


# --- Sustainability ----------------------------------------------------------


def _na(value: float | None, fmt: str) -> str:
    return "not available" if value is None else format(value, fmt)


def sustainability_tab(solution: Solution) -> Any:
    r = solution.response
    m = solution.metrics
    return html.Div(
        [
            dbc.Row(
                [
                    c.stat_card("Estimated CO2", f"{r.estimated_co2_kg:,.3f} kg", note="Total for all routes"),
                    c.stat_card(
                        "CO2 emission factor",
                        f"{r.co2_kg_per_km:.6f} kg/km",
                        note="Configuration parameter of the solve",
                    ),
                    c.stat_card(
                        "Green efficiency",
                        f"{_na(m.co2_per_served_employee_kg, '.3f')} kg"
                        if m.co2_per_served_employee_kg is not None
                        else "not available",
                        note="kg CO2 per employee served (lower is greener)",
                    ),
                ]
            ),
            c.card(
                "Distance efficiency breakdown",
                c.metric_list(
                    [
                        ("Physical distance", f"{r.total_physical_route_distance:,.3f} km"),
                        ("Accounted distance", f"{r.total_modeled_route_distance:,.3f} km"),
                        ("Deadhead distance", f"{r.deadhead_distance_km:,.3f} km"),
                        ("Uncosted distance", f"{m.total_uncosted_distance_km:,.3f} km"),
                        (
                            "Deadhead ratio",
                            f"{_na(m.deadhead_ratio_pct, '.2f')} %"
                            if m.deadhead_ratio_pct is not None
                            else "not available",
                        ),
                    ]
                ),
                html.P(
                    "Deadhead ratio is the share of unproductive travel (repositioning); a lower ratio means "
                    "better efficiency. "
                    "A CO2 gauge and trend are not shown: there is no reference scale or history for them.",
                    className="small text-muted mt-2 mb-0",
                ),
                class_name="mb-3",
            ),
        ]
    )


# --- Summary -----------------------------------------------------------------


def summary_tab(solution: Solution) -> Any:
    specs = tables.kpi_tables(solution)
    items = [
        dbc.AccordionItem(c.data_grid(f"kpi-{key}", specs[key], fit=True), title=title, item_id=key)
        for key, title in SECTION_TITLES.items()
    ]
    return dbc.Accordion(items, always_open=True, active_item=list(SECTION_TITLES), flush=False)
