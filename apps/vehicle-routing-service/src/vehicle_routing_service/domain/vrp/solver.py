"""VRP solver built on OR-Tools.

Ported verbatim from the validated prototype in ``sample/solver.py``. Only the
import paths were adjusted to fit this package's layout; the algorithmic
behavior, callback logic, and result computation are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from vehicle_routing_service.domain.vrp.enums import ServicePointPriority
from vehicle_routing_service.domain.vrp.models import ArcMetrics, RoutingArcCostType, SolverInput

PRIORITY_PENALTY_MULTIPLIERS: dict[ServicePointPriority, int] = {
    ServicePointPriority.LOW: 1,
    ServicePointPriority.MEDIUM: 10,
    ServicePointPriority.HIGH: 100,
}


class SolveStatus(StrEnum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIMEOUT = "TIMEOUT"
    INVALID = "INVALID"
    FAILED = "FAILED"
    NOT_SOLVED = "NOT_SOLVED"


HAS_SOLUTION_STATUSES = {SolveStatus.OPTIMAL, SolveStatus.FEASIBLE}

_ROUTING_STATUS_TO_SOLVE_STATUS: dict[int, SolveStatus] = {
    routing_enums_pb2.RoutingSearchStatus.ROUTING_OPTIMAL: SolveStatus.OPTIMAL,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_SUCCESS: SolveStatus.FEASIBLE,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_PARTIAL_SUCCESS_LOCAL_OPTIMUM_NOT_REACHED: SolveStatus.FEASIBLE,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_INFEASIBLE: SolveStatus.INFEASIBLE,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_FAIL_TIMEOUT: SolveStatus.TIMEOUT,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_INVALID: SolveStatus.INVALID,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_FAIL: SolveStatus.FAILED,
    routing_enums_pb2.RoutingSearchStatus.ROUTING_NOT_SOLVED: SolveStatus.NOT_SOLVED,
}


@dataclass
class RouteStop:
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


@dataclass
class SolvedRoute:
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
    stops: list[RouteStop]


@dataclass
class SolveResult:
    manager: Any
    routing: Any
    time_dimension: Any
    solution: Any
    status: SolveStatus
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



def format_time_from_minutes(total_minutes: float) -> str:
    total_minutes = round(total_minutes)
    days, minutes_day = divmod(total_minutes, 1440)
    hours, minutes = divmod(minutes_day, 60)
    prefix = f"+{days}d " if days > 0 else ""
    return f"{prefix}{hours:02d}:{minutes:02d}"


def hhmm_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Invalid time: {hhmm}")
    return h * 60 + m


def _build_arc_cost_callback(
    routing: Any,
    manager: Any,
    include_first_leg_cost: list[bool],
    include_last_leg_cost: list[bool],
    cost_matrix: list[list[ArcMetrics]],
    routing_arc_cost_type: RoutingArcCostType,
    start_index_to_vehicle: dict[int, int],
    end_index_to_vehicle: dict[int, int],
):
    def arc_cost_callback(from_index: int, to_index: int) -> int:
        if routing.IsStart(from_index) and routing.IsEnd(to_index):
            return 0
        if routing.IsStart(from_index):
            vehicle_node_id = start_index_to_vehicle[from_index]
            if not include_first_leg_cost[vehicle_node_id]:
                return 0
        if routing.IsEnd(to_index):
            vehicle_node_id = end_index_to_vehicle[to_index]
            if not include_last_leg_cost[vehicle_node_id]:
                return 0
        from_node_id = manager.IndexToNode(from_index)
        to_node_id = manager.IndexToNode(to_index)
        arc = cost_matrix[from_node_id][to_node_id]
        if routing_arc_cost_type == RoutingArcCostType.TIME_COST:
            return arc.time_min
        if routing_arc_cost_type == RoutingArcCostType.MIXED_COST:
            return arc.mixed_cost
        return arc.distance_m
    return arc_cost_callback


def _modeled_leg_distance_m(
    routing: Any,
    prev_index: int,
    current_index: int,
    vehicle_node_id: int,
    include_first_leg_cost: list[bool],
    include_last_leg_cost: list[bool],
    distance_m: int,
) -> int:
    if routing.IsStart(prev_index) and routing.IsEnd(current_index):
        return 0
    if routing.IsStart(prev_index) and not include_first_leg_cost[vehicle_node_id]:
        return 0
    if routing.IsEnd(current_index) and not include_last_leg_cost[vehicle_node_id]:
        return 0
    return distance_m


def _reported_leg_distance_m(
    routing: Any,
    prev_index: int,
    current_index: int,
    vehicle_node_id: int,
    include_first_leg_cost: list[bool],
    include_last_leg_cost: list[bool],
    distance_m: int,
) -> int:
    return _modeled_leg_distance_m(
        routing,
        prev_index,
        current_index,
        vehicle_node_id,
        include_first_leg_cost,
        include_last_leg_cost,
        distance_m,
    )


def _reported_leg_time_min(
    routing: Any,
    prev_index: int,
    current_index: int,
    vehicle_node_id: int,
    include_first_leg_time: list[bool],
    include_last_leg_time: list[bool],
    time_min: int,
) -> int:
    if routing.IsStart(prev_index) and routing.IsEnd(current_index):
        return 0
    if routing.IsStart(prev_index) and not include_first_leg_time[vehicle_node_id]:
        return 0
    if routing.IsEnd(current_index) and not include_last_leg_time[vehicle_node_id]:
        return 0
    return time_min


def _reported_drive_time_min(
    routing: Any,
    prev_index: int,
    current_index: int,
    vehicle_node_id: int,
    include_first_leg_time: list[bool],
    include_last_leg_time: list[bool],
    time_min: int,
) -> int:
    return _reported_leg_time_min(
        routing,
        prev_index,
        current_index,
        vehicle_node_id,
        include_first_leg_time,
        include_last_leg_time,
        time_min,
    )


def _classify_stop_type(routing: Any, node_id: int, index: int, service_points_node_offset: int) -> str:
    if routing.IsStart(index):
        return "START"
    if routing.IsEnd(index):
        return "END"
    if node_id >= service_points_node_offset:
        return "SERVICE"
    return "DEPOT"


def _leg_objective_cost(
    routing: Any,
    manager: Any,
    from_index: int,
    to_index: int,
    vehicle_node_id: int,
    include_first_leg_cost: list[bool],
    include_last_leg_cost: list[bool],
    cost_matrix: list[list[ArcMetrics]],
    routing_arc_cost_type: RoutingArcCostType,
) -> int:
    if routing.IsStart(from_index) and routing.IsEnd(to_index):
        return 0
    if routing.IsStart(from_index) and not include_first_leg_cost[vehicle_node_id]:
        return 0
    if routing.IsEnd(to_index) and not include_last_leg_cost[vehicle_node_id]:
        return 0

    from_node_id = manager.IndexToNode(from_index)
    to_node_id = manager.IndexToNode(to_index)
    arc = cost_matrix[from_node_id][to_node_id]
    if routing_arc_cost_type == RoutingArcCostType.TIME_COST:
        return arc.time_min
    if routing_arc_cost_type == RoutingArcCostType.MIXED_COST:
        return arc.mixed_cost
    return arc.distance_m


def _build_time_callback(
    routing: Any,
    manager: Any,
    count_first_leg_time: list[bool],
    count_last_leg_time: list[bool],
    cost_matrix: list[list[ArcMetrics]],
    node_lag_minutes: list[int],
    start_index_to_vehicle: dict[int, int],
    end_index_to_vehicle: dict[int, int],
):
    def time_callback(from_index: int, to_index: int) -> int:
        if routing.IsStart(from_index) and routing.IsEnd(to_index):
            return 0

        if routing.IsStart(from_index):
            vehicle_id = start_index_to_vehicle[from_index]
            if not count_first_leg_time[vehicle_id]:
                return 0

        from_node_id = manager.IndexToNode(from_index)

        if routing.IsEnd(to_index):
            vehicle_id = end_index_to_vehicle[to_index]
            if not count_last_leg_time[vehicle_id]:
                return node_lag_minutes[from_node_id]

        to_node_id = manager.IndexToNode(to_index)

        travel_minutes = cost_matrix[from_node_id][to_node_id].time_min
        return travel_minutes + node_lag_minutes[from_node_id]

    return time_callback


def _build_demand_callback(manager: Any, demands: list[int]):
    def demand_callback(from_index: int) -> int:
        from_node_id = manager.IndexToNode(from_index)
        return demands[from_node_id]

    return demand_callback


def _mean(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _stddev_population(values: list[float]) -> float:
    if not values:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return variance ** 0.5


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * percentile
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = rank - lower_index
    return sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * weight


def _build_infeasibility_hints(problem: SolverInput, time_window_duration: int) -> list[str]:
    hints: list[str] = []
    total_demand = sum(problem.node_demand)
    total_capacity = sum(problem.vehicle_capacities)
    if total_demand > total_capacity:
        hints.append(
            f"Insufficient capacity: total demand {total_demand} exceeds total fleet capacity {total_capacity}."
        )

    service_node_offset = len(problem.node_data) - problem.number_of_service_points
    service_node_ids = list(range(service_node_offset, len(problem.node_data)))
    total_service_minutes = sum(problem.service_point_service_time)
    min_positive_travel = min(
        (
            arc.time_min
            for row in problem.cost_matrix
            for arc in row
            if arc.time_min > 0
        ),
        default=0,
    )
    lower_bound_travel = max(0, problem.number_of_service_points - len(problem.vehicle_start_nodes)) * min_positive_travel
    estimated_required_minutes_lb = total_service_minutes + lower_bound_travel

    available_fleet_minutes = (
        len(problem.vehicle_start_nodes) * time_window_duration
        if problem.time_window_enabled
        else len(problem.vehicle_start_nodes) * problem.max_vehicle_duration_min
    )
    if available_fleet_minutes > 0 and estimated_required_minutes_lb > available_fleet_minutes:
        hints.append(
            "Time may be too tight: optimistic required minutes "
            f"{estimated_required_minutes_lb} exceed available fleet minutes {available_fleet_minutes}."
        )

    if service_node_ids and not hints:
        hints.append(
            "No feasible solution found. Check time-window strictness, first/last leg accounting flags, and omission penalties."
        )
    return hints


def solve_vrp(problem: SolverInput) -> SolveResult:
    node_coords = {node_id: node.coord for node_id, node in problem.node_data.items()}
    node_labels = {node_id: node.label for node_id, node in problem.node_data.items()}

    number_of_coords = len(node_coords)

    number_of_vehicle_start_nodes = len(problem.vehicle_start_nodes)

    if number_of_vehicle_start_nodes != len(problem.vehicle_end_nodes):
        raise ValueError("Initial Depot Nodes and Final Depot Nodes have to have the same length.")

    service_points_node_offset = number_of_coords - problem.number_of_service_points
    if not (0 <= service_points_node_offset <= number_of_coords):
        raise ValueError("The number of service points is inconsistent with the total number of coordinates.")

    time_window_lower_bound = hhmm_to_minutes(problem.time_window_start)
    time_window_upper_bound = hhmm_to_minutes(problem.time_window_end)

    if problem.time_window_crosses_midnight:
        time_window_duration = (time_window_upper_bound + 1440) - time_window_lower_bound
    else:
        time_window_duration = time_window_upper_bound - time_window_lower_bound

    if problem.time_window_enabled and time_window_duration <= 0:
        raise ValueError("Time Window End has to be later than Time Window Start.")

    if number_of_vehicle_start_nodes <= 0:
        raise ValueError("The vehicle start nodes have to be more than 0.")

    if len(problem.service_point_service_time) != problem.number_of_service_points:
        raise ValueError("Service points lag minutes must have exactly one value per service point.")

    if problem.time_window_enabled:
        horizon_min = time_window_duration
        slack_max = time_window_duration
    else:
        horizon_min = problem.max_vehicle_duration_min
        slack_max = problem.max_vehicle_duration_min

    node_service_time = [0] * number_of_coords
    for service_point_enumerator, lag_minutes in enumerate(problem.service_point_service_time):
        node_service_time[service_points_node_offset + service_point_enumerator] = lag_minutes

    manager = pywrapcp.RoutingIndexManager(number_of_coords, number_of_vehicle_start_nodes, problem.vehicle_start_nodes, problem.vehicle_end_nodes)

    routing = pywrapcp.RoutingModel(manager)

    start_index_to_vehicle = {routing.Start(start_node_id): start_node_id for start_node_id in range(number_of_vehicle_start_nodes)}

    end_index_to_vehicle = {routing.End(start_node_id): start_node_id for start_node_id in range(number_of_vehicle_start_nodes)}

    arc_cost_callback = _build_arc_cost_callback(
        routing,
        manager,
        problem.include_first_leg_cost,
        problem.include_last_leg_cost,
        problem.cost_matrix,
        problem.routing_arc_cost_type,
        start_index_to_vehicle,
        end_index_to_vehicle,
    )

    time_callback = _build_time_callback(
        routing,
        manager,
        problem.include_first_leg_time,
        problem.include_last_leg_time,
        problem.cost_matrix,
        node_service_time,
        start_index_to_vehicle,
        end_index_to_vehicle,
    )

    transit_callback_index = routing.RegisterTransitCallback(arc_cost_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, slack_max, horizon_min, False, "Time")

    time_dimension = routing.GetDimensionOrDie("Time")

    if problem.time_window_enabled:
        for vehicle_start_node in range(number_of_vehicle_start_nodes):
            end_index = routing.End(vehicle_start_node)
            time_dimension.CumulVar(end_index).SetMax(time_window_duration)
            start_index = routing.Start(vehicle_start_node)
            if problem.prefer_earliest_departure:
                time_dimension.SetCumulVarSoftUpperBound(start_index, 0, problem.departure_time_preference_penalty)
            else:
                time_dimension.SetCumulVarSoftLowerBound(start_index, time_window_duration, problem.departure_time_preference_penalty)
    else:
        for vehicle_start_node in range(number_of_vehicle_start_nodes):
            time_dimension.SetSpanUpperBoundForVehicle(problem.max_vehicle_duration_min, vehicle_start_node)

    # Slack vars aren't part of the solution assignment by default; reading
    # them via solution.Value(...) without this crashes the process. Only
    # covers non-end indices -- a vehicle's end index has no outgoing arc,
    # so no slack var exists there at all (nothing to wait before).
    for node_index in range(routing.Size()):
        if not routing.IsEnd(node_index):
            routing.AddToAssignment(time_dimension.SlackVar(node_index))

    demand_callback = _build_demand_callback(manager, problem.node_demand)
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, problem.vehicle_capacities, True, "Capacity")
    capacity_dimension = routing.GetDimensionOrDie("Capacity")

    for service_point_node_id, priority in problem.service_point_priorities.items():
        service_point_node_index = manager.NodeToIndex(service_point_node_id)
        priority_multiplier = PRIORITY_PENALTY_MULTIPLIERS[priority]
        omission_penalty = problem.omission_penalty_base * priority_multiplier
        routing.AddDisjunction([service_point_node_index], omission_penalty)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(problem.solver_search_time_limit_seconds)

    solution = routing.SolveWithParameters(search_parameters)
    status = _ROUTING_STATUS_TO_SOLVE_STATUS.get(routing.status(), SolveStatus.FAILED)
    search_wall_time_ms = routing.solver().WallTime()
    solver_branches = routing.solver().Branches()
    solver_failures = routing.solver().Failures()
    solver_status_detail = routing_enums_pb2.RoutingSearchStatus.Value.Name(routing.status())

    if not solution:
        infeasibility_hints = _build_infeasibility_hints(problem, time_window_duration)
        return SolveResult(
            manager=manager,
            routing=routing,
            time_dimension=time_dimension,
            solution=solution,
            status=status,
            omitted_service_points=[],
            solved_routes=[],
            total_covered_service_points=0,
            total_modeled_route_distance=0.0,
            total_physical_route_distance=0.0,
            total_modeled_route_lag=0,
            total_objective_value=0,
            search_wall_time_ms=search_wall_time_ms,
            total_service_points=problem.number_of_service_points,
            service_level_pct=0.0,
            weighted_service_level_pct=0.0,
            served_priority_weight=0,
            total_priority_weight=0,
            omitted_low_priority_count=0,
            omitted_medium_priority_count=0,
            omitted_high_priority_count=0,
            omitted_penalty_low=0,
            omitted_penalty_medium=0,
            omitted_penalty_high=0,
            omitted_penalty_total=0,
            objective_travel_cost=0,
            objective_omission_penalty=0,
            objective_unattributed_cost=0,
            fleet_utilization_pct=0.0,
            workload_balance_demand_std=0.0,
            workload_balance_distance_std=0.0,
            workload_balance_duration_std=0.0,
            max_route_duration_min=0,
            min_route_duration_min=0,
            spread_route_duration_min=0,
            total_drive_min=0,
            total_wait_min=0,
            total_service_min=0,
            deadhead_distance_km=0.0,
            average_stop_wait_min=0.0,
            p95_stop_wait_min=0.0,
            km_per_served_employee=0.0,
            min_per_served_employee=0.0,
            solver_branches=solver_branches,
            solver_failures=solver_failures,
            solver_status_detail=solver_status_detail,
            infeasibility_hints=infeasibility_hints,
            co2_kg_per_km=problem.co2_kg_per_km,
            estimated_co2_kg=0.0,
        )

    omitted_service_points = []
    for service_point_node_id in problem.service_point_priorities:
        service_point_node_index = manager.NodeToIndex(service_point_node_id)
        if solution.Value(routing.NextVar(service_point_node_index)) == service_point_node_index:
            omitted_service_points.append(service_point_node_id)

    time_limit_label = format_time_from_minutes(time_window_lower_bound + time_window_duration) if problem.time_window_enabled else ""
    solved_routes: list[SolvedRoute] = []
    total_route_distance = 0.0
    total_route_physical_distance = 0.0
    total_route_lag = 0
    total_route_service_points = 0
    total_route_drive_time = 0
    total_route_wait_time = 0
    total_deadhead_distance_km = 0.0
    all_stop_wait_minutes: list[float] = []

    for vehicle_start_node in range(number_of_vehicle_start_nodes):
        initial_depot_node_index = routing.Start(vehicle_start_node)
        route_distance = 0
        route_physical_distance = 0.0
        route_lag = 0
        route_drive_time_min = 0
        route_wait_time_min = 0
        route_objective_contribution = 0
        route_service_stops = 0
        priority_low_served = 0
        priority_medium_served = 0
        priority_high_served = 0
        first_service_arrival = ""
        last_service_arrival = ""
        stops: list[RouteStop] = []
        start_t = solution.Value(time_dimension.CumulVar(initial_depot_node_index))
        cumulative_wait_minutes = 0
        cumulative_distance_km = 0.0
        leg_distance_km_from_prev = 0.0
        leg_travel_minutes_from_prev = 0
        stop_sequence = 0
        while not routing.IsEnd(initial_depot_node_index):
            current_index = initial_depot_node_index
            node = manager.IndexToNode(current_index)
            t_arr = solution.Value(time_dimension.CumulVar(current_index))
            wait_minutes = solution.Value(time_dimension.SlackVar(current_index))
            service_minutes = node_service_time[node]
            cumulative_wait_minutes += wait_minutes
            route_wait_time_min += wait_minutes
            load_before = solution.Value(capacity_dimension.CumulVar(current_index))
            if node >= service_points_node_offset:
                route_lag += node_service_time[node]
                route_service_stops += 1
                arrival_label = format_time_from_minutes(time_window_lower_bound + t_arr)
                if not first_service_arrival:
                    first_service_arrival = arrival_label
                last_service_arrival = arrival_label
                node_priority = problem.service_point_priorities[node]
                if node_priority == ServicePointPriority.LOW:
                    priority_low_served += 1
                elif node_priority == ServicePointPriority.MEDIUM:
                    priority_medium_served += 1
                elif node_priority == ServicePointPriority.HIGH:
                    priority_high_served += 1
            prev_index = current_index
            next_index = solution.Value(routing.NextVar(current_index))
            load_after = solution.Value(capacity_dimension.CumulVar(next_index))
            stops.append(
                RouteStop(
                    stop_sequence=stop_sequence,
                    stop_type=_classify_stop_type(routing, node, current_index, service_points_node_offset),
                    node_id=node,
                    node_label=node_labels[node],
                    arrival_minutes=t_arr,
                    arrival_time=format_time_from_minutes(time_window_lower_bound + t_arr),
                    departure_minutes=t_arr + wait_minutes + service_minutes,
                    departure_time=format_time_from_minutes(time_window_lower_bound + t_arr + wait_minutes + service_minutes),
                    service_minutes=service_minutes,
                    wait_minutes=wait_minutes,
                    cumulative_wait_minutes=cumulative_wait_minutes,
                    leg_distance_km_from_prev=leg_distance_km_from_prev,
                    leg_travel_minutes_from_prev=leg_travel_minutes_from_prev,
                    cumulative_distance_km=cumulative_distance_km,
                    load_before=load_before,
                    load_delta=load_after - load_before,
                    load_after=load_after,
                )
            )
            arc_to_next = problem.cost_matrix[node][manager.IndexToNode(next_index)]
            leg_distance_km_from_prev = _reported_leg_distance_m(
                routing,
                prev_index,
                next_index,
                vehicle_start_node,
                problem.include_first_leg_cost,
                problem.include_last_leg_cost,
                arc_to_next.distance_m,
            ) / 1000.0
            leg_travel_minutes_from_prev = _reported_leg_time_min(
                routing,
                prev_index,
                next_index,
                vehicle_start_node,
                problem.include_first_leg_time,
                problem.include_last_leg_time,
                arc_to_next.time_min,
            )
            cumulative_distance_km += leg_distance_km_from_prev
            route_drive_time_min += _reported_drive_time_min(
                routing,
                prev_index,
                next_index,
                vehicle_start_node,
                problem.include_first_leg_time,
                problem.include_last_leg_time,
                arc_to_next.time_min,
            )
            route_objective_contribution += _leg_objective_cost(
                routing,
                manager,
                prev_index,
                next_index,
                vehicle_start_node,
                problem.include_first_leg_cost,
                problem.include_last_leg_cost,
                problem.cost_matrix,
                problem.routing_arc_cost_type,
            )
            route_distance += _modeled_leg_distance_m(
                routing,
                prev_index,
                next_index,
                vehicle_start_node,
                problem.include_first_leg_cost,
                problem.include_last_leg_cost,
                arc_to_next.distance_m,
            )
            route_physical_distance += arc_to_next.distance_m / 1000.0
            if routing.IsStart(prev_index) or routing.IsEnd(next_index):
                total_deadhead_distance_km += arc_to_next.distance_m / 1000.0
            initial_depot_node_index = next_index
            stop_sequence += 1
        end_node = manager.IndexToNode(initial_depot_node_index)
        end_t = solution.Value(time_dimension.CumulVar(initial_depot_node_index))
        covered_demand = solution.Value(capacity_dimension.CumulVar(initial_depot_node_index))
        stops.append(
            RouteStop(
                stop_sequence=stop_sequence,
                stop_type=_classify_stop_type(routing, end_node, initial_depot_node_index, service_points_node_offset),
                node_id=end_node,
                node_label=node_labels[end_node],
                arrival_minutes=end_t,
                arrival_time=format_time_from_minutes(time_window_lower_bound + end_t),
                departure_minutes=end_t,
                departure_time=format_time_from_minutes(time_window_lower_bound + end_t),
                service_minutes=0,
                wait_minutes=0,  # a vehicle's end index has no outgoing arc, so no slack applies here
                cumulative_wait_minutes=cumulative_wait_minutes,
                leg_distance_km_from_prev=leg_distance_km_from_prev,
                leg_travel_minutes_from_prev=leg_travel_minutes_from_prev,
                cumulative_distance_km=cumulative_distance_km,
                load_before=covered_demand,
                load_delta=0,
                load_after=covered_demand,
            )
        )
        initial_depot_label = node_labels[problem.vehicle_start_nodes[vehicle_start_node]]
        final_depot_label = node_labels[problem.vehicle_end_nodes[vehicle_start_node]]
        modeled_route_duration = int(end_t - start_t)
        modeled_route_distance_km = route_distance / 1000.0
        uncosted_distance_km = route_physical_distance - modeled_route_distance_km
        total_service_time_min = route_lag
        productive_time_min = route_drive_time_min + total_service_time_min

        if modeled_route_duration > 0:
            idle_ratio_pct = (route_wait_time_min / modeled_route_duration) * 100.0
            drive_time_pct = (route_drive_time_min / modeled_route_duration) * 100.0
            service_time_pct = (total_service_time_min / modeled_route_duration) * 100.0
            wait_time_pct = (route_wait_time_min / modeled_route_duration) * 100.0
        else:
            idle_ratio_pct = 0.0
            drive_time_pct = 0.0
            service_time_pct = 0.0
            wait_time_pct = 0.0

        if problem.time_window_enabled:
            start_delay_from_window_min = int(start_t)
            remaining_time_to_limit_min = int(time_window_duration - end_t)
        else:
            start_delay_from_window_min = 0
            remaining_time_to_limit_min = int(problem.max_vehicle_duration_min - modeled_route_duration)

        if route_physical_distance > 0:
            distance_efficiency_ratio = modeled_route_distance_km / route_physical_distance
        else:
            distance_efficiency_ratio = 0.0

        if problem.vehicle_capacities[vehicle_start_node] > 0:
            demand_utilization_pct = (covered_demand / problem.vehicle_capacities[vehicle_start_node]) * 100.0
        else:
            demand_utilization_pct = 0.0

        total_stops = len(stops)
        total_service_stops = route_service_stops
        is_empty_route = total_service_stops == 0

        total_route_distance += route_distance
        total_route_physical_distance += route_physical_distance
        total_route_service_points += covered_demand
        total_route_lag += route_lag
        total_route_drive_time += route_drive_time_min
        total_route_wait_time += route_wait_time_min
        all_stop_wait_minutes.extend(float(stop.wait_minutes) for stop in stops)

        solved_routes.append(
            SolvedRoute(
                vehicle_id=vehicle_start_node,
                start_node_label=initial_depot_label,
                end_node_label=final_depot_label,
                covered_demand=covered_demand,
                maximum_demand_coverage=problem.vehicle_capacities[vehicle_start_node],
                demand_utilization_pct=demand_utilization_pct,
                departure_time=format_time_from_minutes(time_window_lower_bound + start_t),
                arrival_time=format_time_from_minutes(time_window_lower_bound + end_t),
                arrival_time_limit=time_limit_label,
                start_delay_from_window_min=start_delay_from_window_min,
                remaining_time_to_limit_min=remaining_time_to_limit_min,
                modeled_route_duration=modeled_route_duration,
                modeled_route_distance=modeled_route_distance_km,
                physical_route_distance=route_physical_distance,
                distance_efficiency_ratio=distance_efficiency_ratio,
                costed_distance_km=modeled_route_distance_km,
                uncosted_distance_km=uncosted_distance_km,
                route_objective_contribution=route_objective_contribution,
                total_stops=total_stops,
                total_service_stops=total_service_stops,
                is_empty_route=is_empty_route,
                first_service_arrival=first_service_arrival,
                last_service_arrival=last_service_arrival,
                priority_low_served=priority_low_served,
                priority_medium_served=priority_medium_served,
                priority_high_served=priority_high_served,
                total_drive_time_min=route_drive_time_min,
                total_wait_time_min=route_wait_time_min,
                total_service_time_min=total_service_time_min,
                productive_time_min=productive_time_min,
                idle_ratio_pct=idle_ratio_pct,
                drive_time_pct=drive_time_pct,
                service_time_pct=service_time_pct,
                wait_time_pct=wait_time_pct,
                service_time=route_lag,
                stops=stops,
            )
        )

    omitted_low_priority_count = 0
    omitted_medium_priority_count = 0
    omitted_high_priority_count = 0
    omitted_penalty_low = 0
    omitted_penalty_medium = 0
    omitted_penalty_high = 0
    for omitted_node in omitted_service_points:
        priority = problem.service_point_priorities[omitted_node]
        penalty = problem.omission_penalty_base * PRIORITY_PENALTY_MULTIPLIERS[priority]
        if priority == ServicePointPriority.LOW:
            omitted_low_priority_count += 1
            omitted_penalty_low += penalty
        elif priority == ServicePointPriority.MEDIUM:
            omitted_medium_priority_count += 1
            omitted_penalty_medium += penalty
        elif priority == ServicePointPriority.HIGH:
            omitted_high_priority_count += 1
            omitted_penalty_high += penalty

    omitted_penalty_total = omitted_penalty_low + omitted_penalty_medium + omitted_penalty_high
    objective_travel_cost = sum(route.route_objective_contribution for route in solved_routes)
    total_objective_value = solution.ObjectiveValue()
    objective_unattributed_cost = total_objective_value - objective_travel_cost - omitted_penalty_total

    total_priority_weight = sum(
        PRIORITY_PENALTY_MULTIPLIERS[priority]
        for priority in problem.service_point_priorities.values()
    )
    served_priority_weight = total_priority_weight - (
        omitted_low_priority_count * PRIORITY_PENALTY_MULTIPLIERS[ServicePointPriority.LOW]
        + omitted_medium_priority_count * PRIORITY_PENALTY_MULTIPLIERS[ServicePointPriority.MEDIUM]
        + omitted_high_priority_count * PRIORITY_PENALTY_MULTIPLIERS[ServicePointPriority.HIGH]
    )

    total_service_points = problem.number_of_service_points
    service_level_pct = (
        (total_route_service_points / total_service_points) * 100.0 if total_service_points > 0 else 0.0
    )
    weighted_service_level_pct = (
        (served_priority_weight / total_priority_weight) * 100.0 if total_priority_weight > 0 else 0.0
    )

    vehicles_used = sum(1 for route in solved_routes if not route.is_empty_route)
    fleet_utilization_pct = (
        (vehicles_used / len(solved_routes)) * 100.0 if solved_routes else 0.0
    )

    operational_routes = [route for route in solved_routes if not route.is_empty_route]
    route_durations = [float(route.modeled_route_duration) for route in operational_routes]
    route_demands = [float(route.covered_demand) for route in operational_routes]
    route_distances = [route.physical_route_distance for route in operational_routes]

    max_route_duration_min = int(max(route_durations)) if route_durations else 0
    min_route_duration_min = int(min(route_durations)) if route_durations else 0
    spread_route_duration_min = max_route_duration_min - min_route_duration_min

    average_stop_wait_min = _mean(all_stop_wait_minutes)
    p95_stop_wait_min = _percentile(all_stop_wait_minutes, 0.95)

    km_per_served_employee = (
        total_route_physical_distance / total_route_service_points if total_route_service_points > 0 else 0.0
    )
    min_per_served_employee = (
        sum(route_durations) / total_route_service_points if total_route_service_points > 0 else 0.0
    )

    estimated_co2_kg = total_route_physical_distance * problem.co2_kg_per_km

    return SolveResult(
        manager=manager,
        routing=routing,
        time_dimension=time_dimension,
        solution=solution,
        status=status,
        omitted_service_points=omitted_service_points,
        solved_routes=solved_routes,
        total_covered_service_points=total_route_service_points,
        total_modeled_route_distance=total_route_distance / 1000.0,
        total_physical_route_distance=total_route_physical_distance,
        total_modeled_route_lag=total_route_lag,
        total_objective_value=total_objective_value,
        search_wall_time_ms=search_wall_time_ms,
        total_service_points=total_service_points,
        service_level_pct=service_level_pct,
        weighted_service_level_pct=weighted_service_level_pct,
        served_priority_weight=served_priority_weight,
        total_priority_weight=total_priority_weight,
        omitted_low_priority_count=omitted_low_priority_count,
        omitted_medium_priority_count=omitted_medium_priority_count,
        omitted_high_priority_count=omitted_high_priority_count,
        omitted_penalty_low=omitted_penalty_low,
        omitted_penalty_medium=omitted_penalty_medium,
        omitted_penalty_high=omitted_penalty_high,
        omitted_penalty_total=omitted_penalty_total,
        objective_travel_cost=objective_travel_cost,
        objective_omission_penalty=omitted_penalty_total,
        objective_unattributed_cost=objective_unattributed_cost,
        fleet_utilization_pct=fleet_utilization_pct,
        workload_balance_demand_std=_stddev_population(route_demands),
        workload_balance_distance_std=_stddev_population(route_distances),
        workload_balance_duration_std=_stddev_population(route_durations),
        max_route_duration_min=max_route_duration_min,
        min_route_duration_min=min_route_duration_min,
        spread_route_duration_min=spread_route_duration_min,
        total_drive_min=total_route_drive_time,
        total_wait_min=total_route_wait_time,
        total_service_min=total_route_lag,
        deadhead_distance_km=total_deadhead_distance_km,
        average_stop_wait_min=average_stop_wait_min,
        p95_stop_wait_min=p95_stop_wait_min,
        km_per_served_employee=km_per_served_employee,
        min_per_served_employee=min_per_served_employee,
        solver_branches=solver_branches,
        solver_failures=solver_failures,
        solver_status_detail=solver_status_detail,
        infeasibility_hints=[],
        co2_kg_per_km=problem.co2_kg_per_km,
        estimated_co2_kg=estimated_co2_kg,
    )
