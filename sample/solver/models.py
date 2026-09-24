from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from enums import ServicePointPriority


class RoutingArcCostType(StrEnum):
    TIME_COST = "TIME_COST"
    DISTANCE_COST = "DISTANCE_COST"
    MIXED_COST = "MIXED_COST"


@dataclass(frozen=True)
class NodeData:
    identifier: str
    coord: tuple[float, float]
    label: str


@dataclass
class ArcMetrics:
    distance_m: int
    time_min: int
    mixed_cost: int


@dataclass
class SolverInput:
    node_data: dict[int, NodeData]
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
    cost_matrix: list[list[ArcMetrics]]
    routing_arc_cost_type: RoutingArcCostType
    omission_penalty_base: int
    solver_search_time_limit_seconds: int
    co2_kg_per_km: float

    @property
    def node_coords(self) -> dict[int, tuple[float, float]]:
        return {node_id: node.coord for node_id, node in self.node_data.items()}

    @property
    def node_labels(self) -> dict[int, str]:
        return {node_id: node.label for node_id, node in self.node_data.items()}