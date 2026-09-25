"""The loaded, validated solution a dashboard renders: response + scenario + derived metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

from vehicle_routing_web.domain.metrics import DerivedMetrics, active_routes
from vehicle_routing_web.domain.scenario import Priority, Scenario
from vehicle_routing_web.domain.solve_response import SolvedRoute, SolveResponse


@dataclass(frozen=True, slots=True)
class OmittedEmployee:
    node_id: int
    label: str
    priority: Priority
    x: float
    y: float


@dataclass(frozen=True)
class Solution:
    process_id: str
    response: SolveResponse
    scenario: Scenario
    metrics: DerivedMetrics
    generated_at: datetime  # modification time of the stored result file

    @cached_property
    def active_routes(self) -> list[SolvedRoute]:
        return active_routes(self.response)

    @cached_property
    def routes_by_vehicle(self) -> dict[int, SolvedRoute]:
        return {route.vehicle_id: route for route in self.response.solved_routes}

    @cached_property
    def omitted_employees(self) -> list[OmittedEmployee]:
        employees: list[OmittedEmployee] = []
        for node_id in self.response.omitted_service_points:
            priority = self.scenario.priority(node_id)
            if priority is None or node_id not in self.scenario.nodes:
                continue  # not an employee node of this payload; never invent a priority
            x, y = self.scenario.coord(node_id)
            employees.append(OmittedEmployee(node_id, self.scenario.label(node_id), priority, x, y))
        return employees
