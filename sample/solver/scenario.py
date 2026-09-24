import math
import random
from dataclasses import dataclass
from enum import StrEnum

from config import Settings
from enums import ServicePointPriority


class EmployeePriorityReferenceLocation(StrEnum):
    INITIAL_DEPOT = "INITIAL_DEPOT"
    FINAL_DEPOT = "FINAL_DEPOT"


class RouteDepotCoordMode(StrEnum):
    SHARED = "SHARED"
    AUTO = "AUTO"
    SPECIFIC = "SPECIFIC"


@dataclass
class Scenario:
    area_min_x: float
    area_max_x: float
    area_min_y: float
    area_max_y: float
    inner_area_x: tuple[float, float]
    inner_area_y: tuple[float, float]
    coord_by_node: dict[int, tuple[float, float]]
    label_by_node: dict[int, str]
    employee_node_offset: int
    employee_nodes: list[int]
    employee_priority_reference_coordinate: tuple[float, float]
    priority_by_employee: dict[int, ServicePointPriority]
    number_of_initial_route_coords: int
    number_of_final_route_coords: int    


def _generate_perimeter_coords(n: int, inner_area_x: tuple[float, float], inner_area_y: tuple[float, float]) -> list[tuple[float, float]]:
    if n <= 0:
        raise ValueError(f"N_VEHICLES ({n}) must be greater than 0 for perimeter auto-distribution.")

    x_min, x_max = inner_area_x
    y_min, y_max = inner_area_y
    dx = x_max - x_min
    dy = y_max - y_min

    perimeter = 2 * (dx + dy)
    # spacing along the perimeter; offset by half spacing to avoid exact corners
    spacing = perimeter / n
    offset = spacing / 2.0

    points: list[tuple[float, float]] = []
    for k in range(n):
        s = (offset + k * spacing) % perimeter
        # side 0: left edge, from (x_min, y_min) -> (x_min, y_max) length dy
        if s < dy:
            x = x_min
            y = y_min + s
        else:
            s -= dy
            # side 1: top edge, from (x_min, y_max) -> (x_max, y_max) length dx
            if s < dx:
                x = x_min + s
                y = y_max
            else:
                s -= dx
                # side 2: right edge, from (x_max, y_max) -> (x_max, y_min) length dy
                if s < dy:
                    x = x_max
                    y = y_max - s
                else:
                    s -= dy
                    # side 3: bottom edge, from (x_max, y_min) -> (x_min, y_min) length dx
                    x = x_max - s
                    y = y_min
        # keep similar precision to generated employee coords
        points.append((round(x, 3), round(y, 3)))

    return points


def _validate_within_subarea(coord: tuple[float, float], coord_name: str, inner_area_x: tuple[float, float], inner_area_y: tuple[float, float]) -> None:
    x, y = coord
    if not (inner_area_x[0] <= x <= inner_area_x[1] and inner_area_y[0] <= y <= inner_area_y[1]):
        raise ValueError(f"{coord_name} {coord} is out of the inner area.")


def _build_side_points(side_point_mode: RouteDepotCoordMode, prefix: str, shared_coord: tuple[float, float], specific_coords: list[tuple[float, float]], number_of_vehicles: int, inner_area_x: tuple[float, float], inner_area_y: tuple[float, float]) -> tuple[list[tuple[float, float]], list[str]]:
    if side_point_mode == RouteDepotCoordMode.SHARED:
        _validate_within_subarea(shared_coord, f"The shared depot {prefix}", inner_area_x, inner_area_y)
        return [shared_coord], [prefix]
    if side_point_mode == RouteDepotCoordMode.AUTO:
        perimeter_coords = _generate_perimeter_coords(number_of_vehicles, inner_area_x, inner_area_y)
        vehicle_labels = [f"{prefix}{i:03d}" for i in range(number_of_vehicles)]
        return perimeter_coords, vehicle_labels
    if len(specific_coords) != number_of_vehicles:
        raise ValueError(f"COORDS_{'INITIAL' if prefix == 'DI' else 'FINAL'}_MANUAL has {len(specific_coords)} elements and must have {number_of_vehicles}.")
    vehicle_labels = [f"{prefix}{i:03d}" for i in range(number_of_vehicles)]
    return list(specific_coords), vehicle_labels


def _centroid(nodes: list[int], coords: dict[int, tuple[float, float]]) -> tuple[float, float]:
    xs = [coords[n][0] for n in nodes]
    ys = [coords[n][1] for n in nodes]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _employee_priority(node_id: int, reference_coord: tuple[float, float], coords: dict[int, tuple[float, float]], low_threshold: float, medium_threshold: float) -> ServicePointPriority:
    xi, yi = coords[node_id]
    xj, yj = reference_coord
    dist = math.hypot(xi - xj, yi - yj)
    if dist <= low_threshold:
        return ServicePointPriority.LOW
    if dist <= medium_threshold:
        return ServicePointPriority.MEDIUM
    return ServicePointPriority.HIGH


def build_scenario(settings: Settings) -> Scenario:
    if settings.average_speed_kmh <= 0:
        raise ValueError("AVERAGE_SPEED_KMH must be greater than 0.")

    random.seed(settings.random_seed)
    area_min_x = settings.area_min_x
    area_max_x = settings.area_max_x
    area_min_y = settings.area_min_y
    area_max_y = settings.area_max_y
    inner_area_x = (area_min_x + settings.inner_area_margin_km, area_max_x - settings.inner_area_margin_km)
    inner_area_y = (area_min_y + settings.inner_area_margin_km, area_max_y - settings.inner_area_margin_km)
    if not (inner_area_x[0] < inner_area_x[1] and inner_area_y[0] < inner_area_y[1]):
        raise ValueError("INNER_AREA_MARGIN_KM is too large for the defined area.")

    initial_depot_coords, initial_depot_labels = _build_side_points(
        RouteDepotCoordMode(settings.route_initial_depot_coord_mode),
        "DI",
        settings.shared_initial_depot_coord,
        list(settings.specific_initial_depot_coords),
        settings.number_of_vehicles,
        inner_area_x,
        inner_area_y,
    )
    final_depot_coords, final_depot_labels = _build_side_points(
        RouteDepotCoordMode(settings.route_final_depot_coord_mode),
        "DF",
        settings.shared_final_depot_coord,
        list(settings.specific_final_depot_coords),
        settings.number_of_vehicles,
        inner_area_x,
        inner_area_y,
    )

    number_of_initial_depot_coords = len(initial_depot_coords)
    number_of_final_depot_coords = len(final_depot_coords)
    
    initial_depot_nodes = list(range(number_of_initial_depot_coords))
    final_depot_nodes = list(range(number_of_initial_depot_coords, number_of_initial_depot_coords + number_of_final_depot_coords))
    
    employee_node_offset = number_of_initial_depot_coords + number_of_final_depot_coords
    
    dict_coord_by_node: dict[int, tuple[float, float]] = {}
    for node, coord in zip(initial_depot_nodes, initial_depot_coords):
        dict_coord_by_node[node] = coord
    for node, coord in zip(final_depot_nodes, final_depot_coords):
        dict_coord_by_node[node] = coord

    dict_label_by_node: dict[int, str] = {}
    for node, label in zip(initial_depot_nodes, initial_depot_labels):
        dict_label_by_node[node] = label
    for node, label in zip(final_depot_nodes, final_depot_labels):
        dict_label_by_node[node] = label

    list_employee_nodes: list[int] = []
    for i in range(settings.number_of_employees):
        employee_node_id = employee_node_offset + i
        dict_coord_by_node[employee_node_id] = (
            round(random.uniform(inner_area_x[0], inner_area_x[1]), 3),
            round(random.uniform(inner_area_y[0], inner_area_y[1]), 3),
        )
        list_employee_nodes.append(employee_node_id)
        dict_label_by_node[employee_node_id] = f"E{i}"

    employee_priority_reference_location = EmployeePriorityReferenceLocation(settings.employee_priority_reference_location)
    nodes_for_employee_priority_reference = initial_depot_nodes if employee_priority_reference_location == EmployeePriorityReferenceLocation.INITIAL_DEPOT else final_depot_nodes
    
    employee_priority_reference_coord = _centroid(nodes_for_employee_priority_reference, dict_coord_by_node)

    dict_priority_by_employee = {
        employee_node_id: _employee_priority(
            employee_node_id,
            employee_priority_reference_coord,
            dict_coord_by_node,
            settings.low_priority_employee_max_km,
            settings.medium_priority_employee_max_km,
        ) for employee_node_id in list_employee_nodes
    }

    return Scenario(
        area_min_x=area_min_x,
        area_max_x=area_max_x,
        area_min_y=area_min_y,
        area_max_y=area_max_y,
        inner_area_x=inner_area_x,
        inner_area_y=inner_area_y,
        coord_by_node=dict_coord_by_node,
        label_by_node=dict_label_by_node,
        employee_node_offset=employee_node_offset,
        employee_nodes=list_employee_nodes,        
        employee_priority_reference_coordinate=employee_priority_reference_coord,
        priority_by_employee=dict_priority_by_employee,
        number_of_initial_route_coords=number_of_initial_depot_coords,
        number_of_final_route_coords=number_of_final_depot_coords        
    )
