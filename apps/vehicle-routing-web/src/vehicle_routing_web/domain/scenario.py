"""The parts of the uploaded payload the dashboard needs (coordinates, labels, priorities, vehicle config).

The solver response carries route results only; node coordinates, labels and
employee priorities exist solely in the payload. The large ``cost_matrix`` is
deliberately not modelled (extra keys are ignored), so it is never retained.

Coordinates are planar x/y values (kilometres in the reference scenario), not
latitude/longitude.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

Priority = Literal["low", "medium", "high"]
PRIORITIES: tuple[Priority, ...] = ("low", "medium", "high")


class PayloadNode(BaseModel):
    identifier: str
    coord: tuple[float, float]
    label: str


class Scenario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nodes: dict[int, PayloadNode]
    service_point_priorities: dict[int, Priority]
    vehicle_start_nodes: list[int]
    vehicle_end_nodes: list[int]
    vehicle_capacities: list[int]
    include_first_leg_cost: list[bool]
    include_first_leg_time: list[bool]
    include_last_leg_cost: list[bool]
    include_last_leg_time: list[bool]
    time_window_start: str
    time_window_end: str
    max_vehicle_duration_min: int

    @model_validator(mode="after")
    def _references_exist(self) -> Scenario:
        known = set(self.nodes)
        referenced = {*self.service_point_priorities, *self.vehicle_start_nodes, *self.vehicle_end_nodes}
        if not referenced <= known:
            raise ValueError("Payload references node ids that are not defined in 'nodes'.")
        return self

    def coord(self, node_id: int) -> tuple[float, float]:
        return self.nodes[node_id].coord

    def label(self, node_id: int) -> str:
        return self.nodes[node_id].label

    def priority(self, node_id: int) -> Priority | None:
        return self.service_point_priorities.get(node_id)

    @property
    def employee_node_ids(self) -> list[int]:
        return sorted(self.service_point_priorities)

    def leg_counted(self, vehicle_id: int, *, first: bool) -> tuple[bool, bool]:
        """``(cost counted, time counted)`` for a vehicle's first or last leg."""
        costs = self.include_first_leg_cost if first else self.include_last_leg_cost
        times = self.include_first_leg_time if first else self.include_last_leg_time
        try:
            return costs[vehicle_id], times[vehicle_id]
        except IndexError:
            return True, True
