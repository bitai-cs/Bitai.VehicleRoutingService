"""Application use case orchestrating the VRP solve operation.

The use case is intentionally thin: this is a single, stateless,
compute-only capability with no persistence and no cross-aggregate
orchestration, so a full CQRS/ports layout would be disproportionate.

Responsibilities:
    - Accept a `SolveVrpCommand` (a plain application-layer DTO composed of
      domain value objects) built by the presentation layer from the HTTP
      request.
    - Translate the command into the domain `SolverInput` aggregate
      (`node_data` is a `dict[int, NodeData]` keyed by contiguous node id,
      per the domain contract).
    - Invoke the domain `solve_vrp` function off the event loop, since it is
      a synchronous, potentially long-running CPU-bound OR-Tools search.
    - Return the domain `SolveResult` unchanged; the presentation layer is
      responsible for translating it into an API response schema and for
      excluding the non-serializable OR-Tools internals
      (`manager`, `routing`, `time_dimension`, `solution`).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool

from vehicle_routing_service.domain.vrp.enums import ServicePointPriority
from vehicle_routing_service.domain.vrp.models import (
    ArcMetrics,
    NodeData,
    RoutingArcCostType,
    SolverInput,
)
from vehicle_routing_service.domain.vrp.solver import SolveResult, solve_vrp


@dataclass
class SolveVrpCommand:
    """Application-layer input for the solve-VRP use case.

    `nodes` mirrors `SolverInput.node_data` (`dict[int, NodeData]`): its keys
    are the contiguous node ids used throughout `service_point_priorities`,
    `vehicle_start_nodes`/`vehicle_end_nodes`, and `cost_matrix`. Contiguity
    is validated at the presentation boundary (`SolveVrpRequest`), not here.
    """

    nodes: dict[int, NodeData]
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

    def to_solver_input(self) -> SolverInput:
        return SolverInput(
            node_data=dict(self.nodes),
            node_demand=self.node_demand,
            number_of_service_points=self.number_of_service_points,
            service_point_service_time=self.service_point_service_time,
            service_point_priorities=self.service_point_priorities,
            vehicle_start_nodes=self.vehicle_start_nodes,
            vehicle_end_nodes=self.vehicle_end_nodes,
            vehicle_capacities=self.vehicle_capacities,
            time_window_start=self.time_window_start,
            time_window_end=self.time_window_end,
            time_window_crosses_midnight=self.time_window_crosses_midnight,
            time_window_enabled=self.time_window_enabled,
            prefer_earliest_departure=self.prefer_earliest_departure,
            departure_time_preference_penalty=self.departure_time_preference_penalty,
            max_vehicle_duration_min=self.max_vehicle_duration_min,
            include_first_leg_cost=self.include_first_leg_cost,
            include_first_leg_time=self.include_first_leg_time,
            include_last_leg_cost=self.include_last_leg_cost,
            include_last_leg_time=self.include_last_leg_time,
            cost_matrix=self.cost_matrix,
            routing_arc_cost_type=self.routing_arc_cost_type,
            omission_penalty_base=self.omission_penalty_base,
            solver_search_time_limit_seconds=self.solver_search_time_limit_seconds,
            co2_kg_per_km=self.co2_kg_per_km,
        )


class SolveVrpUseCase:
    """Orchestrates a single VRP solve operation."""

    async def execute(self, command: SolveVrpCommand) -> SolveResult:
        solver_input = command.to_solver_input()
        return await run_in_threadpool(solve_vrp, solver_input)
