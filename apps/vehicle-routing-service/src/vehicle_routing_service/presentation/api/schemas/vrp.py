"""Pydantic v2 request/response schemas for the VRP solve endpoint.

These schemas are the HTTP boundary contract. They intentionally do not
duplicate `solve_vrp`'s own business validation (e.g. time-window
consistency, list-length cross-checks) -- that validation already exists in
the domain function and its `ValueError`s are translated into HTTP 422
responses by the registered exception handler. Pydantic here is responsible
only for structural/type validation and for shaping data at the boundary.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from vehicle_routing_service.application.vrp.solve_vrp_use_case import SolveVrpCommand
from vehicle_routing_service.domain.vrp.enums import ServicePointPriority
from vehicle_routing_service.domain.vrp.models import (
    ArcMetrics,
    NodeData,
    RoutingArcCostType,
)
from vehicle_routing_service.domain.vrp.solver import SolveResult, SolveStatus


class NodeSchema(BaseModel):
    identifier: str
    coord: tuple[float, float]
    label: str


class ArcMetricsSchema(BaseModel):
    distance_m: int
    time_min: int
    mixed_cost: int


class SolveVrpRequest(BaseModel):
    """Mirrors `SolverInput`, including `node_data`'s `dict[int, NodeData]` shape.

    `nodes` keys are node ids and must be contiguous starting at 0 (`0..N-1`,
    no gaps) -- those same ids are used positionally elsewhere in this
    payload (`service_point_priorities`, `vehicle_start_nodes`,
    `vehicle_end_nodes`, `cost_matrix`), so a gap or an out-of-range id would
    desynchronize this payload from itself. That contiguity is enforced by
    `_nodes_must_be_contiguous` below.
    """

    nodes: dict[int, NodeSchema]
    node_demand: list[int]
    number_of_service_points: int
    service_point_service_time: list[int]
    service_point_priorities: dict[int, ServicePointPriority]
    vehicle_start_nodes: list[int]
    vehicle_end_nodes: list[int]
    vehicle_capacities: list[int]
    time_window_start: str
    time_window_end: str
    time_window_crosses_midnight: bool
    time_window_enabled: bool
    prefer_earliest_departure: bool
    departure_time_preference_penalty: int
    max_vehicle_duration_min: int
    include_first_leg_cost: list[bool]
    include_first_leg_time: list[bool]
    include_last_leg_cost: list[bool]
    include_last_leg_time: list[bool]
    cost_matrix: list[list[ArcMetricsSchema]]
    routing_arc_cost_type: RoutingArcCostType
    omission_penalty_base: int
    solver_search_time_limit_seconds: int
    co2_kg_per_km: float

    @model_validator(mode="after")
    def _nodes_must_be_contiguous(self) -> SolveVrpRequest:
        if set(self.nodes.keys()) != set(range(len(self.nodes))):
            raise ValueError(
                "nodes keys must be contiguous node ids starting at 0 (0..N-1, no gaps or out-of-range ids)."
            )
        return self

    def to_command(self) -> SolveVrpCommand:
        return SolveVrpCommand(
            nodes={
                node_id: NodeData(identifier=node.identifier, coord=node.coord, label=node.label)
                for node_id, node in self.nodes.items()
            },
            node_demand=list(self.node_demand),
            number_of_service_points=self.number_of_service_points,
            service_point_service_time=list(self.service_point_service_time),
            service_point_priorities=dict(self.service_point_priorities),
            vehicle_start_nodes=list(self.vehicle_start_nodes),
            vehicle_end_nodes=list(self.vehicle_end_nodes),
            vehicle_capacities=list(self.vehicle_capacities),
            time_window_start=self.time_window_start,
            time_window_end=self.time_window_end,
            time_window_crosses_midnight=self.time_window_crosses_midnight,
            time_window_enabled=self.time_window_enabled,
            prefer_earliest_departure=self.prefer_earliest_departure,
            departure_time_preference_penalty=self.departure_time_preference_penalty,
            max_vehicle_duration_min=self.max_vehicle_duration_min,
            include_first_leg_cost=list(self.include_first_leg_cost),
            include_first_leg_time=list(self.include_first_leg_time),
            include_last_leg_cost=list(self.include_last_leg_cost),
            include_last_leg_time=list(self.include_last_leg_time),
            cost_matrix=[
                [ArcMetrics(distance_m=arc.distance_m, time_min=arc.time_min, mixed_cost=arc.mixed_cost) for arc in row]
                for row in self.cost_matrix
            ],
            routing_arc_cost_type=self.routing_arc_cost_type,
            omission_penalty_base=self.omission_penalty_base,
            solver_search_time_limit_seconds=self.solver_search_time_limit_seconds,
            co2_kg_per_km=self.co2_kg_per_km,
        )


class RouteStopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class SolvedRouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    first_service_arrival: str
    last_service_arrival: str
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
    service_time: int
    stops: list[RouteStopResponse]


class SolveVrpResponse(BaseModel):
    """Mirrors `SolveResult`, excluding the non-serializable OR-Tools
    internals (`manager`, `routing`, `time_dimension`, `solution`).

    Built via `model_validate(result)` with `from_attributes=True`: only the
    fields declared below are read off the domain `SolveResult`, so the
    excluded fields are never touched or serialized.
    """

    model_config = ConfigDict(from_attributes=True)

    status: SolveStatus
    omitted_service_points: list[int]
    solved_routes: list[SolvedRouteResponse]
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

    @classmethod
    def from_domain(cls, result: SolveResult) -> SolveVrpResponse:
        return cls.model_validate(result)
