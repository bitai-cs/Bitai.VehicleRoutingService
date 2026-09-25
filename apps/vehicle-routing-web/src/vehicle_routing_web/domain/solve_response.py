"""Boundary contract for the solver response (mirrors the service's ``SolveVrpResponse``).

Unknown extra fields are tolerated so a service upgrade that only adds fields
does not break this app, but every field the dashboard relies on is required
and typed. The validated JSON is stored as received.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow")


class RouteStop(_Tolerant):
    stop_sequence: int
    stop_type: str
    node_id: int
    node_label: str
    arrival_minutes: int
    arrival_time: str
    departure_minutes: int
    departure_time: str
    service_minutes: int
    wait_minutes: int
    cumulative_wait_minutes: int
    leg_distance_km_from_prev: float
    leg_travel_minutes_from_prev: int
    cumulative_distance_km: float
    load_before: int
    load_delta: int
    load_after: int


class SolvedRoute(_Tolerant):
    vehicle_id: int
    start_node_label: str
    end_node_label: str
    covered_demand: int
    maximum_demand_coverage: int
    demand_utilization_pct: float
    departure_time: str
    arrival_time: str
    remaining_time_to_limit_min: int
    modeled_route_duration: int
    modeled_route_distance: float
    physical_route_distance: float
    total_service_stops: int
    is_empty_route: bool
    total_drive_time_min: int
    total_wait_time_min: int
    total_service_time_min: int
    stops: list[RouteStop]


class SolveResponse(_Tolerant):
    status: str
    omitted_service_points: list[int]
    solved_routes: list[SolvedRoute]
    total_covered_service_points: int
    total_modeled_route_distance: float
    total_physical_route_distance: float
    total_objective_value: int
    search_wall_time_ms: int
    total_service_points: int
    service_level_pct: float
