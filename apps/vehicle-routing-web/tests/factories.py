"""Small, hand-verifiable solution used across dashboard tests.

Geometry/time numbers are chosen so expected metrics can be computed by hand:

* v0: START -> E3 -> E4 -> E5 -> END, duration 60, drive 40, service 15, wait 5, 20 km, 3 stops, 60% util
* v1: START -> E6 -> E7 -> END,       duration 40, drive 30, service 10, wait 0, 15 km, 2 stops, 40% util
* v2: empty route
* node 8 (high priority) is omitted
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from vehicle_routing_web.domain.metrics import compute_metrics
from vehicle_routing_web.domain.scenario import Scenario
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.domain.solve_response import SolveResponse

LABELS = {0: "DI", 1: "DF1", 2: "DF2", 3: "E3", 4: "E4", 5: "E5", 6: "E6", 7: "E7", 8: "E8"}
COORDS = {
    0: (0.0, 0.0),
    1: (10.0, 0.0),
    2: (0.0, 10.0),
    3: (2.0, 1.0),
    4: (4.0, 2.0),
    5: (6.0, 3.0),
    6: (1.0, 4.0),
    7: (1.0, 8.0),
    8: (-5.0, -5.0),
}
PRIORITIES = {3: "low", 4: "medium", 5: "high", 6: "high", 7: "low", 8: "high"}


def _hhmm(minutes: int) -> str:
    total = 7 * 60 + 30 + minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def _route(vehicle_id: int, end_node: int, legs: list[tuple[int, int, int, int]], capacity: int = 5) -> dict[str, Any]:
    """``legs`` are (node_id, travel_min, wait_min, service_min); the last leg is the END stop."""
    stops = [
        {
            "stop_sequence": 0, "stop_type": "START", "node_id": 0, "node_label": "DI",
            "arrival_minutes": 0, "arrival_time": _hhmm(0), "departure_minutes": 0, "departure_time": _hhmm(0),
            "service_minutes": 0, "wait_minutes": 0, "cumulative_wait_minutes": 0,
            "leg_distance_km_from_prev": 0.0, "leg_travel_minutes_from_prev": 0, "cumulative_distance_km": 0.0,
            "load_before": 0, "load_delta": 0, "load_after": 0,
        }
    ]  # fmt: skip
    clock = 0
    distance = 0.0
    waited = 0
    load = 0
    for seq, (node, travel, wait, service) in enumerate(legs, start=1):
        arrival = clock + travel + wait
        departure = arrival + service
        leg_km = travel * 0.5
        distance += leg_km
        waited += wait
        is_end = seq == len(legs)
        delta = 0 if is_end else 1
        stops.append(
            {
                "stop_sequence": seq, "stop_type": "END" if is_end else "SERVICE", "node_id": node,
                "node_label": LABELS[node], "arrival_minutes": arrival, "arrival_time": _hhmm(arrival),
                "departure_minutes": departure, "departure_time": _hhmm(departure), "service_minutes": service,
                "wait_minutes": wait, "cumulative_wait_minutes": waited, "leg_distance_km_from_prev": leg_km,
                "leg_travel_minutes_from_prev": travel, "cumulative_distance_km": distance,
                "load_before": load, "load_delta": delta, "load_after": load + delta,
            }
        )  # fmt: skip
        load += delta
        clock = departure
    service_legs = legs[:-1]
    drive = sum(leg[1] for leg in legs)
    service = sum(leg[3] for leg in service_legs)
    wait = sum(leg[2] for leg in legs)
    duration = clock
    empty = not service_legs
    first_leg_km = legs[0][1] * 0.5
    return {
        "vehicle_id": vehicle_id, "start_node_label": "DI", "end_node_label": LABELS[end_node],
        "covered_demand": len(service_legs), "maximum_demand_coverage": capacity,
        "demand_utilization_pct": len(service_legs) / capacity * 100, "departure_time": _hhmm(0),
        "arrival_time": _hhmm(duration), "arrival_time_limit": "09:00", "start_delay_from_window_min": 0,
        "remaining_time_to_limit_min": 90 - duration, "modeled_route_duration": duration,
        "modeled_route_distance": distance, "physical_route_distance": distance,
        "distance_efficiency_ratio": 1.0, "costed_distance_km": distance - (first_leg_km if vehicle_id == 0 else 0),
        "uncosted_distance_km": first_leg_km if vehicle_id == 0 else 0.0, "route_objective_contribution": 0,
        "total_stops": len(stops), "total_service_stops": len(service_legs), "is_empty_route": empty,
        "priority_low_served": 0, "priority_medium_served": 0, "priority_high_served": 0,
        "total_drive_time_min": drive, "total_wait_time_min": wait, "total_service_time_min": service,
        "productive_time_min": drive + service, "idle_ratio_pct": 0.0, "drive_time_pct": 0.0,
        "service_time_pct": 0.0, "wait_time_pct": 0.0, "stops": stops,
    }  # fmt: skip


def make_response_dict() -> dict[str, Any]:
    v0 = _route(0, 1, [(3, 10, 0, 5), (4, 10, 5, 5), (5, 10, 0, 5), (1, 10, 0, 0)])
    v1 = _route(1, 2, [(6, 20, 0, 5), (7, 5, 0, 5), (2, 5, 0, 0)])
    v2 = _route(2, 1, [(1, 0, 0, 0)])
    return {
        "status": "FEASIBLE", "omitted_service_points": [8], "solved_routes": [v0, v1, v2],
        "total_covered_service_points": 5, "total_modeled_route_distance": 30.0,
        "total_physical_route_distance": 35.0, "total_modeled_route_lag": 25, "total_objective_value": 1000,
        "search_wall_time_ms": 1234, "total_service_points": 6, "service_level_pct": 5 / 6 * 100,
        "weighted_service_level_pct": 71.43, "served_priority_weight": 10, "total_priority_weight": 14,
        "omitted_low_priority_count": 0, "omitted_medium_priority_count": 0, "omitted_high_priority_count": 1,
        "omitted_penalty_low": 0, "omitted_penalty_medium": 0, "omitted_penalty_high": 300,
        "omitted_penalty_total": 300, "objective_travel_cost": 695, "objective_omission_penalty": 300,
        "objective_unattributed_cost": 5, "fleet_utilization_pct": 2 / 3 * 100,
        "workload_balance_demand_std": 0.5, "workload_balance_distance_std": 2.5,
        "workload_balance_duration_std": 10.0, "max_route_duration_min": 60, "min_route_duration_min": 40,
        "spread_route_duration_min": 20, "total_drive_min": 70, "total_wait_min": 5, "total_service_min": 25,
        "deadhead_distance_km": 22.5, "average_stop_wait_min": 1.0, "p95_stop_wait_min": 4.0,
        "km_per_served_employee": 7.0, "min_per_served_employee": 20.0, "solver_branches": 500,
        "solver_failures": 20, "solver_status_detail": "ROUTING_SUCCESS", "infeasibility_hints": [],
        "co2_kg_per_km": 0.2, "estimated_co2_kg": 7.0,
    }  # fmt: skip


def make_payload_dict() -> dict[str, Any]:
    return {
        "nodes": {str(n): {"identifier": f"id-{n}", "coord": list(COORDS[n]), "label": LABELS[n]} for n in LABELS},
        "node_demand": [0] * 9,
        "number_of_service_points": 6,
        "service_point_priorities": {str(n): p for n, p in PRIORITIES.items()},
        "vehicle_start_nodes": [0, 0, 0],
        "vehicle_end_nodes": [1, 2, 1],
        "vehicle_capacities": [5, 5, 5],
        "include_first_leg_cost": [True, False, True],
        "include_first_leg_time": [True, True, True],
        "include_last_leg_cost": [True, True, False],
        "include_last_leg_time": [True, True, False],
        "time_window_start": "07:30",
        "time_window_end": "09:00",
        "max_vehicle_duration_min": 90,
        "cost_matrix": [[{"distance_m": 1, "time_min": 1, "mixed_cost": 1}]],
    }


def make_solution(
    process_id: str = "demo", *, response: dict[str, Any] | None = None, payload: dict[str, Any] | None = None
) -> Solution:
    parsed = SolveResponse.model_validate(copy.deepcopy(response or make_response_dict()))
    return Solution(
        process_id=process_id,
        response=parsed,
        scenario=Scenario.model_validate(payload or make_payload_dict()),
        metrics=compute_metrics(parsed),
        generated_at=datetime(2026, 9, 24, 12, 0, tzinfo=UTC),
    )
