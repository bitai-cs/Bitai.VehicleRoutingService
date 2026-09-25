"""Boundary contract for the solver response (mirrors the service's ``SolveVrpResponse``).

Field names and types follow ``vehicle-routing-service``
(``presentation/api/schemas/vrp.py``). Unknown extra fields are tolerated so a
service upgrade that only adds fields does not break this app, but every field
the dashboard relies on is required and typed. The validated JSON is stored as
received.
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
    arrival_time_limit: str
    start_delay_from_window_min: int
    remaining_time_to_limit_min: int
    modeled_route_duration: int
    modeled_route_distance: float
    physical_route_distance: float
    distance_efficiency_ratio: float
    costed_distance_km: float
    uncosted_distance_km: float
    route_objective_contribution: int
    total_stops: int
    total_service_stops: int
    is_empty_route: bool
    priority_low_served: int
    priority_medium_served: int
    priority_high_served: int
    total_drive_time_min: int
    total_wait_time_min: int
    total_service_time_min: int
    productive_time_min: int
    idle_ratio_pct: float
    drive_time_pct: float
    service_time_pct: float
    wait_time_pct: float
    stops: list[RouteStop]


class SolveResponse(_Tolerant):
    status: str
    omitted_service_points: list[int]
    solved_routes: list[SolvedRoute]
    total_covered_service_points: int
    total_modeled_route_distance: float
    total_physical_route_distance: float
    total_modeled_route_lag: int
    total_objective_value: int
    search_wall_time_ms: int
    total_service_points: int
    service_level_pct: float
    weighted_service_level_pct: float
    served_priority_weight: int
    total_priority_weight: int
    omitted_low_priority_count: int
    omitted_medium_priority_count: int
    omitted_high_priority_count: int
    omitted_penalty_low: int
    omitted_penalty_medium: int
    omitted_penalty_high: int
    omitted_penalty_total: int
    objective_travel_cost: int
    objective_omission_penalty: int
    objective_unattributed_cost: int
    fleet_utilization_pct: float
    workload_balance_demand_std: float
    workload_balance_distance_std: float
    workload_balance_duration_std: float
    max_route_duration_min: int
    min_route_duration_min: int
    spread_route_duration_min: int
    total_drive_min: int
    total_wait_min: int
    total_service_min: int
    deadhead_distance_km: float
    average_stop_wait_min: float
    p95_stop_wait_min: float
    km_per_served_employee: float
    min_per_served_employee: float
    solver_branches: int
    solver_failures: int
    solver_status_detail: str
    infeasibility_hints: list[str]
    co2_kg_per_km: float
    estimated_co2_kg: float
