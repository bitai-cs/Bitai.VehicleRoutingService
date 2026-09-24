from __future__ import annotations

from uuid import uuid4

from config import Settings
from models import ArcMetrics, NodeData, RoutingArcCostType, SolverInput
from scenario import RouteDepotCoordMode, Scenario


def _euclidean_distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _build_cost_matrix(
    coord_by_node: dict[int, tuple[float, float]],
    average_speed_kmh: float,
    arc_cost_time_factor: float,
    arc_cost_distance_factor: float,
) -> list[list[ArcMetrics]]:
    number_of_coords = len(coord_by_node)
    coords = [coord_by_node[i] for i in range(number_of_coords)]
    matrix: list[list[ArcMetrics]] = []
    for i in range(number_of_coords):
        row = []
        for j in range(number_of_coords):
            distance_km = _euclidean_distance_km(coords[i], coords[j])
            distance_m = round(distance_km * 1000.0)
            time_min = round((distance_km / average_speed_kmh) * 60.0)
            mixed_cost = round((time_min * arc_cost_time_factor) + (distance_m * arc_cost_distance_factor))
            row.append(ArcMetrics(distance_m=distance_m, time_min=time_min, mixed_cost=mixed_cost))
        matrix.append(row)
    return matrix


def build_solver_input(settings: Settings, scenario: Scenario) -> SolverInput:
    if settings.number_of_vehicles <= 0:
        raise ValueError("Number of vehicles have to be greater than 0.")

    if settings.route_initial_depot_coord_mode == RouteDepotCoordMode.SHARED:
        starts = [0] * settings.number_of_vehicles
    else:
        starts = list(range(scenario.number_of_initial_route_coords))

    if settings.route_final_depot_coord_mode == RouteDepotCoordMode.SHARED:
        ends = [scenario.number_of_initial_route_coords] * settings.number_of_vehicles
    else:
        ends = list(range(scenario.number_of_initial_route_coords, scenario.number_of_initial_route_coords + scenario.number_of_final_route_coords))

    node_demand = [0] * len(scenario.coord_by_node) # scenario.number_of_nodes
    for node_id, demand in zip(scenario.employee_nodes, settings.demand_per_employee):
        node_demand[node_id] = demand

    node_data = {
        node_id: NodeData(
            identifier=str(uuid4()),
            coord=scenario.coord_by_node[node_id],
            label=scenario.label_by_node[node_id],
        )
        for node_id in scenario.coord_by_node
    }

    return SolverInput(
        node_data=node_data,
        node_demand=node_demand,
        number_of_service_points=settings.number_of_employees,
        service_point_service_time=list(settings.lag_minutes_per_employee),        
        service_point_priorities=dict(scenario.priority_by_employee),
        vehicle_start_nodes=starts,
        vehicle_end_nodes=ends,
        vehicle_capacities=list(settings.capacity_per_vehicle),
        time_window_start=settings.time_window_start_time,
        time_window_end=settings.time_window_end_time,
        time_window_crosses_midnight=settings.time_window_end_time_crosses_midnight,
        time_window_enabled=settings.use_time_window,
        prefer_earliest_departure=settings.prefer_earliest_departure,
        departure_time_preference_penalty=settings.time_preference_penalty,
        max_vehicle_duration_min=settings.max_route_duration_min,
        include_first_leg_cost=list(settings.count_first_leg_cost),
        include_first_leg_time=list(settings.count_first_leg_time),
        include_last_leg_cost=list(settings.count_last_leg_cost),
        include_last_leg_time=list(settings.count_last_leg_time),
        cost_matrix=_build_cost_matrix(
            scenario.coord_by_node,
            settings.average_speed_kmh,
            settings.arc_cost_time_factor,
            settings.arc_cost_distance_factor,
        ),
        routing_arc_cost_type=RoutingArcCostType(settings.routing_arc_cost_type),
        omission_penalty_base=settings.omission_penalty_base,
        solver_search_time_limit_seconds=settings.solution_timeout_seconds,
        co2_kg_per_km=settings.co2_kg_per_km,
    )
