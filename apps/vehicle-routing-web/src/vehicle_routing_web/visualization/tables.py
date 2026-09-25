"""AG Grid table specifications (pure data; no Dash imports).

Each builder returns a :class:`TableSpec` with typed canonical values (numbers
stay numbers so sorting/filtering are semantic) and a stable ``row_id`` field.
Row highlighting uses precomputed band fields plus ``rowClassRules`` that map
to CSS classes in ``assets/dashboard.css``; every highlighted state is also
present as text in a column, so colour is never the only signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vehicle_routing_web.domain.kpi_table import SECTION_TITLES, build_kpi_rows
from vehicle_routing_web.domain.scenario import PRIORITIES
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.domain.thresholds import Rating

MAX_STOP_ROWS = 5000  # upper bound on rows shipped to the browser for the stops table
PRIORITY_RANK = {p: i + 1 for i, p in enumerate(PRIORITIES)}

_NUM = {"type": "rightAligned", "filter": "agNumberColumnFilter"}
_TEXT = {"filter": "agTextColumnFilter"}


@dataclass(frozen=True)
class TableSpec:
    column_defs: list[dict[str, Any]]
    row_data: list[dict[str, Any]]
    row_id: str
    row_class_rules: dict[str, str] = field(default_factory=dict)
    truncated: bool = False


def _col(field_: str, header: str, kind: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    return {"field": field_, "headerName": header, **(kind or _TEXT), **extra}


def omitted_table(solution: Solution) -> TableSpec:
    rows = [
        {
            "node_id": e.node_id,
            "employee": e.label,
            "priority": e.priority,
            "priority_rank": PRIORITY_RANK[e.priority],
            "x_km": round(e.x, 3),
            "y_km": round(e.y, 3),
        }
        for e in solution.omitted_employees
    ]
    columns = [
        _col("node_id", "Node ID", _NUM, width=110),
        _col("employee", "Employee", flex=1, minWidth=120),
        _col("priority", "Priority", width=120),
        _col("priority_rank", "Priority rank (1=low)", _NUM, width=170),
        _col("x_km", "x (km)", _NUM, width=110),
        _col("y_km", "y (km)", _NUM, width=110),
    ]
    rules = {
        "row-priority-high": "params.data.priority === 'high'",
        "row-priority-medium": "params.data.priority === 'medium'",
    }
    return TableSpec(columns, rows, "node_id", rules)


def _util_band(pct: float) -> str:
    return "low" if pct < 60 else "mid" if pct <= 85 else "high"


def routes_table(solution: Solution) -> TableSpec:
    rows = [
        {
            "vehicle_id": r.vehicle_id,
            "origin": r.start_node_label,
            "destination": r.end_node_label,
            "modeled_duration_min": r.modeled_route_duration,
            "physical_distance_km": round(r.physical_route_distance, 3),
            "demand_utilization_pct": round(r.demand_utilization_pct, 2),
            "total_service_stops": r.total_service_stops,
            "empty_route": "Yes" if r.is_empty_route else "No",
            "util_band": "none" if r.is_empty_route else _util_band(r.demand_utilization_pct),
        }
        for r in sorted(solution.response.solved_routes, key=lambda r: r.vehicle_id)
    ]
    columns = [
        _col("vehicle_id", "Vehicle", _NUM, width=110),
        _col("origin", "Origin", width=120),
        _col("destination", "Destination", width=130),
        _col("modeled_duration_min", "Duration (min)", _NUM, width=150),
        _col("physical_distance_km", "Distance (km)", _NUM, width=150),
        _col("demand_utilization_pct", "Demand util. (%)", _NUM, width=160),
        _col("total_service_stops", "Service stops", _NUM, width=140),
        _col("empty_route", "Empty route", width=130, floatingFilter=True),
    ]
    rules = {
        "row-util-low": "params.data.util_band === 'low'",
        "row-util-mid": "params.data.util_band === 'mid'",
        "row-util-high": "params.data.util_band === 'high'",
    }
    return TableSpec(columns, rows, "vehicle_id", rules)


def _wait_band(minutes: int) -> str:
    return "none" if minutes <= 0 else "some" if minutes <= 5 else "high"


def stops_table(solution: Solution, vehicle_id: int | None) -> TableSpec:
    routes = (
        [solution.routes_by_vehicle[vehicle_id]]
        if vehicle_id is not None and vehicle_id in solution.routes_by_vehicle
        else sorted(solution.active_routes, key=lambda r: r.vehicle_id)
    )
    rows: list[dict[str, Any]] = []
    truncated = False
    for route in routes:
        for s in route.stops:
            if len(rows) >= MAX_STOP_ROWS:
                truncated = True
                break
            rows.append(
                {
                    "stop_key": f"{route.vehicle_id}-{s.stop_sequence}",
                    "vehicle_id": route.vehicle_id,
                    "stop_sequence": s.stop_sequence,
                    "stop_type": s.stop_type,
                    "node_label": s.node_label,
                    "arrival_time": s.arrival_time,
                    "arrival_minutes": s.arrival_minutes,
                    "departure_time": s.departure_time,
                    "service_minutes": s.service_minutes,
                    "wait_minutes": s.wait_minutes,
                    "load_before": s.load_before,
                    "load_delta": s.load_delta,
                    "load_after": s.load_after,
                    "leg_distance_km_from_prev": round(s.leg_distance_km_from_prev, 3),
                    "leg_travel_minutes_from_prev": s.leg_travel_minutes_from_prev,
                    "cumulative_distance_km": round(s.cumulative_distance_km, 3),
                    "cumulative_wait_minutes": s.cumulative_wait_minutes,
                    "wait_band": _wait_band(s.wait_minutes) if s.stop_type == "SERVICE" else "edge",
                }
            )
    columns = [
        _col("vehicle_id", "Vehicle", _NUM, width=100),
        _col("stop_sequence", "Seq.", _NUM, width=90),
        _col("stop_type", "Type", width=110),
        _col("node_label", "Node", width=120),
        _col("arrival_time", "Arrival", width=110),
        _col("arrival_minutes", "Arrival (min)", _NUM, width=130),
        _col("departure_time", "Departure", width=120),
        _col("service_minutes", "Service (min)", _NUM, width=130),
        _col("wait_minutes", "Wait (min)", _NUM, width=120),
        _col("load_before", "Load before", _NUM, width=120),
        _col("load_delta", "Load delta", _NUM, width=120),
        _col("load_after", "Load after", _NUM, width=120),
        _col("leg_distance_km_from_prev", "Leg dist. (km)", _NUM, width=140),
        _col("leg_travel_minutes_from_prev", "Leg time (min)", _NUM, width=140),
        _col("cumulative_distance_km", "Cum. dist. (km)", _NUM, width=150),
        _col("cumulative_wait_minutes", "Cum. wait (min)", _NUM, width=150),
    ]
    rules = {
        "row-edge": "params.data.wait_band === 'edge'",
        "row-wait-some": "params.data.wait_band === 'some'",
        "row-wait-high": "params.data.wait_band === 'high'",
    }
    return TableSpec(columns, rows, "stop_key", rules, truncated)


_RATING_CLASS_RULES = {f"row-rating-{r.value}": f"params.data.rating === '{r.value}'" for r in Rating}


def kpi_tables(solution: Solution) -> dict[str, TableSpec]:
    """One table per KPI section, keyed by section id (order follows ``SECTION_TITLES``)."""
    grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in SECTION_TITLES}
    for row in build_kpi_rows(solution):
        value = None if row.value is None else round(float(row.value), 6)
        grouped[row.section].append(
            {
                "metric": row.metric,
                "value": value,
                "unit": row.unit,
                "target": row.target,
                "status": row.rating.label if value is not None else "Not available",
                "rating": row.rating.value if value is not None else Rating.INFO.value,
                "interpretation": row.interpretation,
            }
        )
    columns = [
        _col("metric", "Metric", flex=2, minWidth=220),
        _col("value", "Value", _NUM, width=140),
        _col("unit", "Unit", width=90),
        _col("target", "Target", flex=1, minWidth=170),
        _col("status", "Status", width=140),
        _col("interpretation", "Interpretation", flex=3, minWidth=260),
    ]
    return {key: TableSpec(columns, rows, "metric", _RATING_CLASS_RULES) for key, rows in grouped.items()}
