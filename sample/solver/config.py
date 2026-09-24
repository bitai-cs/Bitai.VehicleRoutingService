import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

ENV_PREFIX = "UCMSME_"
DEFAULT_CO2_KG_PER_KM = 0.192


@dataclass
class Settings:
    env_file: str
    area_min_x: float
    area_max_x: float
    area_min_y: float
    area_max_y: float
    inner_area_margin_km: float
    random_seed: int | None
    number_of_employees: int
    number_of_vehicles: int
    capacity_per_vehicle: list[int]
    arc_cost_time_factor: float
    arc_cost_distance_factor: float
    routing_arc_cost_type: str
    demand_per_employee: list[int]
    lag_minutes_per_employee: list[int]
    route_initial_depot_coord_mode: str
    shared_initial_depot_coord: tuple[float, float]
    specific_initial_depot_coords: list[tuple[float, float]]
    route_final_depot_coord_mode: str
    shared_final_depot_coord: tuple[float, float]
    specific_final_depot_coords: list[tuple[float, float]]
    count_first_leg_cost: list[bool]
    count_first_leg_time: list[bool]
    count_last_leg_cost: list[bool]
    count_last_leg_time: list[bool]
    use_time_window: bool
    time_window_start_time: str
    time_window_end_time: str
    time_window_end_time_crosses_midnight: bool
    max_route_duration_min: int
    prefer_earliest_departure: bool
    time_preference_penalty: int
    average_speed_kmh: float
    low_priority_employee_max_km: float
    medium_priority_employee_max_km: float
    employee_priority_reference_location: str
    omission_penalty_base: int
    co2_kg_per_km: float
    solution_timeout_seconds: int
    plot_scenario: bool
    plot_all_routes: bool
    output_dir: str
    scenario_plot_filename: str
    route_plot_filename_template: str
    route_details_csv_filename: str
    route_stop_details_csv_filename: str
    solution_summary_csv_filename: str
    omitted_employees_csv_filename: str
    operational_kpis_csv_filename: str
    plot_figsize: tuple[int, int]
    plot_dpi: int
    plot_savefig_bbox: str
    plot_initial_marker: str
    plot_initial_size: float
    plot_initial_color: str
    plot_initial_label: str
    plot_final_marker: str
    plot_final_size: float
    plot_final_color: str
    plot_final_label: str
    plot_employee_marker: str
    plot_employee_size: float
    plot_employee_color: str
    plot_employee_alpha: float
    plot_employee_label: str
    plot_dropped_employee_color: str
    plot_dropped_employee_marker: str
    plot_dropped_employee_size: float
    plot_dropped_employee_label: str
    plot_node_label_offset: tuple[int, int]
    plot_small_label_fontsize: int
    plot_employee_id_label_offset: tuple[int, int]
    plot_employee_id_label_color: str
    plot_visit_order_label_offset: tuple[int, int]
    plot_x_label: str
    plot_y_label: str
    plot_grid_line_style: str
    plot_grid_alpha: float
    plot_legend_loc: str
    plot_legend_bbox_to_anchor: tuple[float, float]
    plot_legend_border_axes_pad: float
    plot_route_color: str
    plot_route_line_width: float
    plot_route_point_size: float
    plot_empty_route_line_style: tuple[Any, ...] | None
    plot_empty_route_label: str
    plot_leg_both_counted_line_style: str
    plot_leg_mixed_counted_line_style: str
    plot_leg_not_counted_line_style: str


ENVVAR_DESCRIPTOR: dict[str, str] = {
    "AREA_MIN_X": "Minimum value for X axis.",
    "AREA_MAX_X": "Maximum value for X axis.",
    "AREA_MIN_Y": "Minimum value for Y axis.",
    "AREA_MAX_Y": "Maximum value for Y axis.",
    "INNER_AREA_MARGIN_KM": "Inner frame margin in km.",
    "RANDOM_SEED": "Random seed integer, or 'none' to disable seeding.",
    "NUMBER_OF_EMPLOYEES": "Number of employees/service points.",
    "NUMBER_OF_VEHICLES": "Number of vehicles/routes.",
    "CAPACITY_PER_VEHICLE": "JSON list with one capacity per vehicle.",
    "ARC_COST_TIME_FACTOR": "Weight applied to time_min when computing an arc's mixed_cost.",
    "ARC_COST_DISTANCE_FACTOR": "Weight applied to distance_m when computing an arc's mixed_cost.",
    "ROUTING_ARC_COST_TYPE": "Arc cost used by the solver's objective: TIME_COST, DISTANCE_COST, or MIXED_COST.",
    "DEMAND_PER_EMPLOYEE": "JSON list with one demand value per employee.",
    "LAG_MINUTES_PER_EMPLOYEE": "JSON list with one service lag value per employee.",
    "ROUTE_INITIAL_DEPOT_COORD_MODE": "Initial depot mode: SHARED, AUTO, or SPECIFIC.",
    "SHARED_INITIAL_DEPOT_COORD": "JSON [x, y] coordinate for the shared initial depot.",
    "SPECIFIC_INITIAL_DEPOT_COORDS": "JSON list of [x, y] coordinates for manual initial depots.",
    "ROUTE_FINAL_DEPOT_COORD_MODE": "Final depot mode: SHARED, AUTO, or SPECIFIC.",
    "SHARED_FINAL_DEPOT_COORD": "JSON [x, y] coordinate for the shared final depot.",
    "SPECIFIC_FINAL_DEPOT_COORDS": "JSON list of [x, y] coordinates for manual final depots.",
    "COUNT_FIRST_LEG_COST": "JSON list of booleans, one per vehicle.",
    "COUNT_FIRST_LEG_TIME": "JSON list of booleans, one per vehicle.",
    "COUNT_LAST_LEG_COST": "JSON list of booleans, one per vehicle.",
    "COUNT_LAST_LEG_TIME": "JSON list of booleans, one per vehicle.",
    "USE_TIME_WINDOW": "Boolean enabling time-window constraints.",
    "TIME_WINDOW_START_TIME": "Start time in HH:MM.",
    "TIME_WINDOW_END_TIME": "End time in HH:MM.",
    "TIME_WINDOW_END_TIME_CROSSES_MIDNIGHT": "Boolean indicating whether the time window crosses midnight.",
    "MAX_ROUTE_DURATION_MIN": "Maximum route duration in minutes.",
    "PREFER_EARLIEST_DEPARTURE": "Boolean for departure-time preference direction.",
    "TIME_PREFERENCE_PENALTY": "Soft penalty used for departure-time preference.",
    "AVERAGE_SPEED_KMH": "Average travel speed in km/h.",
    "LOW_PRIORITY_EMPLOYEE_MAX_KM": "Distance threshold for low priority.",
    "MEDIUM_PRIORITY_EMPLOYEE_MAX_KM": "Distance threshold for medium priority.",
    "EMPLOYEE_PRIORITY_REFERENCE_LOCATION": "Priority reference side: INITIAL_DEPOT or FINAL_DEPOT.",
    "OMISSION_PENALTY_BASE": "Base omission penalty used by the solver.",
    "SOLUTION_TIMEOUT_SECONDS": "Solver time limit in seconds.",
    "PLOT_SCENARIO": "Boolean to generate the scenario plot.",
    "PLOT_ALL_ROUTES": "Boolean to generate route plots.",
    "PLOT_FIGSIZE": "JSON [width, height] for the matplotlib figure size.",
    "PLOT_DPI": "Plot DPI.",
    "PLOT_SAVEFIG_BBOX": "Matplotlib bbox_inches value.",
    "PLOT_INICIAL_MARKER": "Marker for initial depots.",
    "PLOT_INICIAL_SIZE": "Marker size for initial depots.",
    "PLOT_INICIAL_COLOR": "Color for initial depots.",
    "PLOT_INICIAL_LABEL": "Legend label for initial depots.",
    "PLOT_FINAL_MARKER": "Marker for final depots.",
    "PLOT_FINAL_SIZE": "Marker size for final depots.",
    "PLOT_FINAL_COLOR": "Color for final depots.",
    "PLOT_FINAL_LABEL": "Legend label for final depots.",
    "PLOT_EMPLOYEE_MARKER": "Marker for employees.",
    "PLOT_EMPLOYEE_SIZE": "Marker size for employees.",
    "PLOT_EMPLOYEE_COLOR": "Color for employees.",
    "PLOT_EMPLOYEE_ALPHA": "Alpha for employee markers.",
    "PLOT_EMPLOYEE_LABEL": "Legend label for employees.",
    "PLOT_DROPPED_EMPLOYEE_COLOR": "Color for dropped employees.",
    "PLOT_DROPPED_EMPLOYEE_MARKER": "Marker for dropped employees.",
    "PLOT_DROPPED_EMPLOYEE_SIZE": "Marker size for dropped employees.",
    "PLOT_DROPPED_EMPLOYEE_LABEL": "Legend label for dropped employees.",
    "PLOT_NODE_LABEL_OFFSET": "JSON [dx, dy] offset for depot labels.",
    "PLOT_SMALL_LABEL_FONTSIZE": "Font size for small labels.",
    "PLOT_EMPLOYEE_ID_LABEL_OFFSET": "JSON [dx, dy] offset for employee id labels.",
    "PLOT_EMPLOYEE_ID_LABEL_COLOR": "Color for employee id labels.",
    "PLOT_VISIT_ORDER_LABEL_OFFSET": "JSON [dx, dy] offset for visit order labels.",
    "PLOT_XLABEL": "X axis label.",
    "PLOT_YLABEL": "Y axis label.",
    "PLOT_GRID_LINESTYLE": "Grid linestyle.",
    "PLOT_GRID_ALPHA": "Grid alpha.",
    "PLOT_LEGEND_LOC": "Legend location.",
    "PLOT_LEGEND_BBOX_TO_ANCHOR": "JSON [x, y] legend bbox anchor.",
    "PLOT_LEGEND_BORDERAXESPAD": "Legend borderaxespad.",
    "PLOT_ROUTE_COLOR": "Color for route lines.",
    "PLOT_ROUTE_LINE_WIDTH": "Line width for routes.",
    "PLOT_ROUTE_POINT_SIZE": "Point size for route nodes.",
    "PLOT_EMPTY_ROUTE_LINESTYLE": "JSON linestyle tuple/list, or 'none'.",
    "PLOT_EMPTY_ROUTE_LABEL": "Legend label for empty routes.",
    "PLOT_LEG_BOTH_COUNTED_LINESTYLE": "Linestyle for a first/last route leg whose cost AND time are both counted.",
    "PLOT_LEG_MIXED_COUNTED_LINESTYLE": "Linestyle for a first/last route leg where only cost OR only time is counted.",
    "PLOT_LEG_NOT_COUNTED_LINESTYLE": "Linestyle for a first/last route leg whose cost AND time are both NOT counted.",
}

BOOL_KEYS = {
    "USE_TIME_WINDOW",
    "TIME_WINDOW_END_TIME_CROSSES_MIDNIGHT",
    "PREFER_EARLIEST_DEPARTURE",
    "PLOT_SCENARIO",
    "PLOT_ALL_ROUTES",
}

INT_KEYS = {
    "NUMBER_OF_EMPLOYEES",
    "NUMBER_OF_VEHICLES",
    "MAX_ROUTE_DURATION_MIN",
    "TIME_PREFERENCE_PENALTY",
    "OMISSION_PENALTY_BASE",
    "SOLUTION_TIMEOUT_SECONDS",
    "PLOT_DPI",
    "PLOT_SMALL_LABEL_FONTSIZE",
}

FLOAT_KEYS = {
    "AREA_MIN_X",
    "AREA_MAX_X",
    "AREA_MIN_Y",
    "AREA_MAX_Y",
    "INNER_AREA_MARGIN_KM",
    "ARC_COST_TIME_FACTOR",
    "ARC_COST_DISTANCE_FACTOR",
    "AVERAGE_SPEED_KMH",
    "LOW_PRIORITY_EMPLOYEE_MAX_KM",
    "MEDIUM_PRIORITY_EMPLOYEE_MAX_KM",
    "PLOT_INICIAL_SIZE",
    "PLOT_FINAL_SIZE",
    "PLOT_EMPLOYEE_SIZE",
    "PLOT_EMPLOYEE_ALPHA",
    "PLOT_DROPPED_EMPLOYEE_SIZE",
    "PLOT_GRID_ALPHA",
    "PLOT_LEGEND_BORDERAXESPAD",
    "PLOT_ROUTE_LINE_WIDTH",
    "PLOT_ROUTE_POINT_SIZE",
}

JSON_KEYS = {
    "CAPACITY_PER_VEHICLE",
    "DEMAND_PER_EMPLOYEE",
    "LAG_MINUTES_PER_EMPLOYEE",
    "SHARED_INITIAL_DEPOT_COORD",
    "SPECIFIC_INITIAL_DEPOT_COORDS",
    "SHARED_FINAL_DEPOT_COORD",
    "SPECIFIC_FINAL_DEPOT_COORDS",
    "COUNT_FIRST_LEG_COST",
    "COUNT_FIRST_LEG_TIME",
    "COUNT_LAST_LEG_COST",
    "COUNT_LAST_LEG_TIME",
    "PLOT_FIGSIZE",
    "PLOT_NODE_LABEL_OFFSET",
    "PLOT_EMPLOYEE_ID_LABEL_OFFSET",
    "PLOT_VISIT_ORDER_LABEL_OFFSET",
    "PLOT_LEGEND_BBOX_TO_ANCHOR",
    "PLOT_EMPTY_ROUTE_LINESTYLE",
}


def _parse_bool(raw: Any) -> bool:
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {raw!r}")


def _parse_json_value(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {raw!r}") from exc
    return raw


def _parse_value(name: str, raw: Any) -> Any:
    if name in BOOL_KEYS:
        return _parse_bool(raw)
    if name == "RANDOM_SEED":
        text = str(raw).strip().lower()
        if text == "none":
            return None
        return int(raw)
    if name in INT_KEYS:
        return int(raw)
    if name in FLOAT_KEYS:
        return float(raw)
    if name in JSON_KEYS:
        text = str(raw).strip().lower()
        if name == "PLOT_EMPTY_ROUTE_LINESTYLE" and text == "none":
            return None
        return _parse_json_value(raw)
    return str(raw)


def _ensure_required_values(env_path: Path) -> dict[str, Any]:
    file_values = dotenv_values(env_path)
    resolved: dict[str, Any] = {}
    errors: list[str] = []

    for name, description in ENVVAR_DESCRIPTOR.items():
        env_name = f"{ENV_PREFIX}{name}"
        raw = os.environ.get(env_name)
        if raw is None:
            raw = file_values.get(env_name)

        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            errors.append(f"- {env_name}: missing or empty. {description}")
            continue

        try:
            resolved[name] = _parse_value(name, raw)
        except (TypeError, ValueError) as exc:
            errors.append(f"- {env_name}: invalid value ({exc}). {description}")

    if errors:
        print(
            "Configuration is invalid. Define every required UCMSME_ variable in the .env file or environment.\n"
            + "\n".join(errors)
        )
        sys.exit(1)

    return resolved


def load_settings(env_file: str = ".env") -> Settings:
    base_path = Path(__file__).resolve().parent
    env_path = (base_path / env_file).resolve()
    if not env_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {env_path}")

    resolved = _ensure_required_values(env_path)
    file_values = dotenv_values(env_path)

    co2_env_name = f"{ENV_PREFIX}CO2_KG_PER_KM"
    co2_raw = os.environ.get(co2_env_name)
    if co2_raw is None:
        co2_raw = file_values.get(co2_env_name)
    if co2_raw is None or (isinstance(co2_raw, str) and co2_raw.strip() == ""):
        resolved["CO2_KG_PER_KM"] = DEFAULT_CO2_KG_PER_KM
    else:
        try:
            resolved["CO2_KG_PER_KM"] = float(co2_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{co2_env_name} invalid: {co2_raw!r} ({exc})") from exc

    env_filename = env_path.name
    base_name = "default" if env_filename == ".env" else Path(env_filename).stem

    resolved["OUTPUT_DIR"] = f"./output_{base_name}"
    resolved["SCENARIO_PLOT_FILENAME"] = f"{base_name}-vrp.png"
    resolved["ROUTE_PLOT_FILENAME_TEMPLATE"] = f"{base_name}-route-{{vehicle}}.png"
    resolved["ROUTE_DETAILS_CSV_FILENAME"] = f"{base_name}-route-details.csv"
    resolved["ROUTE_STOP_DETAILS_CSV_FILENAME"] = f"{base_name}-stop-details.csv"
    resolved["SOLUTION_SUMMARY_CSV_FILENAME"] = f"{base_name}-solution-summary.csv"
    resolved["OMITTED_EMPLOYEES_CSV_FILENAME"] = f"{base_name}-omitted_employees.csv"
    resolved["OPERATIONAL_KPIS_CSV_FILENAME"] = f"{base_name}-operational-kpis.csv"

    output_dir = resolved["OUTPUT_DIR"]
    if isinstance(output_dir, str) and not os.path.isabs(output_dir):
        resolved["OUTPUT_DIR"] = str((base_path / output_dir).resolve())

    number_of_employees = int(resolved["NUMBER_OF_EMPLOYEES"])
    number_of_vehicles = int(resolved["NUMBER_OF_VEHICLES"])

    capacity_per_vehicle = [int(value) for value in resolved["CAPACITY_PER_VEHICLE"]]
    demand_per_employee = [int(value) for value in resolved["DEMAND_PER_EMPLOYEE"]]
    lag_minutes_per_employee = [int(value) for value in resolved["LAG_MINUTES_PER_EMPLOYEE"]]

    count_first_leg_cost = [bool(value) for value in resolved["COUNT_FIRST_LEG_COST"]]
    count_first_leg_time = [bool(value) for value in resolved["COUNT_FIRST_LEG_TIME"]]
    count_last_leg_cost = [bool(value) for value in resolved["COUNT_LAST_LEG_COST"]]
    count_last_leg_time = [bool(value) for value in resolved["COUNT_LAST_LEG_TIME"]]

    if len(capacity_per_vehicle) != number_of_vehicles:
        raise ValueError("UCMSME_CAPACITY_PER_VEHICLE must have exactly NUMBER_OF_VEHICLES values.")
    if len(demand_per_employee) != number_of_employees:
        raise ValueError("UCMSME_DEMAND_PER_EMPLOYEE must have exactly NUMBER_OF_EMPLOYEES values.")
    if len(lag_minutes_per_employee) != number_of_employees:
        raise ValueError("UCMSME_LAG_MINUTES_PER_EMPLOYEE must have exactly NUMBER_OF_EMPLOYEES values.")
    if any(value < 0 for value in lag_minutes_per_employee):
        raise ValueError("UCMSME_LAG_MINUTES_PER_EMPLOYEE does not allow negative values.")
    if len(count_first_leg_cost) != number_of_vehicles:
        raise ValueError("UCMSME_COUNT_FIRST_LEG_COST must have exactly NUMBER_OF_VEHICLES values.")
    if len(count_first_leg_time) != number_of_vehicles:
        raise ValueError("UCMSME_COUNT_FIRST_LEG_TIME must have exactly NUMBER_OF_VEHICLES values.")
    if len(count_last_leg_cost) != number_of_vehicles:
        raise ValueError("UCMSME_COUNT_LAST_LEG_COST must have exactly NUMBER_OF_VEHICLES values.")
    if len(count_last_leg_time) != number_of_vehicles:
        raise ValueError("UCMSME_COUNT_LAST_LEG_TIME must have exactly NUMBER_OF_VEHICLES values.")

    shared_initial_depot_coord = tuple(resolved["SHARED_INITIAL_DEPOT_COORD"])
    shared_final_depot_coord = tuple(resolved["SHARED_FINAL_DEPOT_COORD"])
    specific_initial_depot_coords = [tuple(item) for item in resolved["SPECIFIC_INITIAL_DEPOT_COORDS"]]
    specific_final_depot_coords = [tuple(item) for item in resolved["SPECIFIC_FINAL_DEPOT_COORDS"]]

    settings = Settings(
        env_file=env_file,
        area_min_x=float(resolved["AREA_MIN_X"]),
        area_max_x=float(resolved["AREA_MAX_X"]),
        area_min_y=float(resolved["AREA_MIN_Y"]),
        area_max_y=float(resolved["AREA_MAX_Y"]),
        inner_area_margin_km=float(resolved["INNER_AREA_MARGIN_KM"]),
        random_seed=resolved["RANDOM_SEED"],
        number_of_employees=number_of_employees,
        number_of_vehicles=number_of_vehicles,
        capacity_per_vehicle=capacity_per_vehicle,
        arc_cost_time_factor=float(resolved["ARC_COST_TIME_FACTOR"]),
        arc_cost_distance_factor=float(resolved["ARC_COST_DISTANCE_FACTOR"]),
        routing_arc_cost_type=str(resolved["ROUTING_ARC_COST_TYPE"]),
        demand_per_employee=demand_per_employee,
        lag_minutes_per_employee=lag_minutes_per_employee,
        route_initial_depot_coord_mode=str(resolved["ROUTE_INITIAL_DEPOT_COORD_MODE"]),
        shared_initial_depot_coord=shared_initial_depot_coord, 
        specific_initial_depot_coords=specific_initial_depot_coords,
        route_final_depot_coord_mode=str(resolved["ROUTE_FINAL_DEPOT_COORD_MODE"]),
        shared_final_depot_coord=shared_final_depot_coord,
        specific_final_depot_coords=specific_final_depot_coords,
        count_first_leg_cost=count_first_leg_cost,
        count_first_leg_time=count_first_leg_time,
        count_last_leg_cost=count_last_leg_cost,
        count_last_leg_time=count_last_leg_time,
        use_time_window=bool(resolved["USE_TIME_WINDOW"]),
        time_window_start_time=str(resolved["TIME_WINDOW_START_TIME"]),
        time_window_end_time=str(resolved["TIME_WINDOW_END_TIME"]),
        time_window_end_time_crosses_midnight=bool(resolved["TIME_WINDOW_END_TIME_CROSSES_MIDNIGHT"]),
        max_route_duration_min=int(resolved["MAX_ROUTE_DURATION_MIN"]),
        prefer_earliest_departure=bool(resolved["PREFER_EARLIEST_DEPARTURE"]),
        time_preference_penalty=int(resolved["TIME_PREFERENCE_PENALTY"]),
        average_speed_kmh=float(resolved["AVERAGE_SPEED_KMH"]),
        low_priority_employee_max_km=float(resolved["LOW_PRIORITY_EMPLOYEE_MAX_KM"]),
        medium_priority_employee_max_km=float(resolved["MEDIUM_PRIORITY_EMPLOYEE_MAX_KM"]),
        employee_priority_reference_location=str(resolved["EMPLOYEE_PRIORITY_REFERENCE_LOCATION"]),
        omission_penalty_base=int(resolved["OMISSION_PENALTY_BASE"]),
        co2_kg_per_km=float(resolved["CO2_KG_PER_KM"]),
        solution_timeout_seconds=int(resolved["SOLUTION_TIMEOUT_SECONDS"]),
        plot_scenario=bool(resolved["PLOT_SCENARIO"]),
        plot_all_routes=bool(resolved["PLOT_ALL_ROUTES"]),
        output_dir=str(resolved["OUTPUT_DIR"]),
        scenario_plot_filename=str(resolved["SCENARIO_PLOT_FILENAME"]),
        route_plot_filename_template=str(resolved["ROUTE_PLOT_FILENAME_TEMPLATE"]),
        route_details_csv_filename=str(resolved["ROUTE_DETAILS_CSV_FILENAME"]),
        route_stop_details_csv_filename=str(resolved["ROUTE_STOP_DETAILS_CSV_FILENAME"]),
        solution_summary_csv_filename=str(resolved["SOLUTION_SUMMARY_CSV_FILENAME"]),
        omitted_employees_csv_filename=str(resolved["OMITTED_EMPLOYEES_CSV_FILENAME"]),
        operational_kpis_csv_filename=str(resolved["OPERATIONAL_KPIS_CSV_FILENAME"]),
        plot_figsize=tuple(resolved["PLOT_FIGSIZE"]),
        plot_dpi=int(resolved["PLOT_DPI"]),
        plot_savefig_bbox=str(resolved["PLOT_SAVEFIG_BBOX"]),
        plot_initial_marker=str(resolved["PLOT_INICIAL_MARKER"]),
        plot_initial_size=float(resolved["PLOT_INICIAL_SIZE"]),
        plot_initial_color=str(resolved["PLOT_INICIAL_COLOR"]),
        plot_initial_label=str(resolved["PLOT_INICIAL_LABEL"]),
        plot_final_marker=str(resolved["PLOT_FINAL_MARKER"]),
        plot_final_size=float(resolved["PLOT_FINAL_SIZE"]),
        plot_final_color=str(resolved["PLOT_FINAL_COLOR"]),
        plot_final_label=str(resolved["PLOT_FINAL_LABEL"]),
        plot_employee_marker=str(resolved["PLOT_EMPLOYEE_MARKER"]),
        plot_employee_size=float(resolved["PLOT_EMPLOYEE_SIZE"]),
        plot_employee_color=str(resolved["PLOT_EMPLOYEE_COLOR"]),
        plot_employee_alpha=float(resolved["PLOT_EMPLOYEE_ALPHA"]),
        plot_employee_label=str(resolved["PLOT_EMPLOYEE_LABEL"]),
        plot_dropped_employee_color=str(resolved["PLOT_DROPPED_EMPLOYEE_COLOR"]),
        plot_dropped_employee_marker=str(resolved["PLOT_DROPPED_EMPLOYEE_MARKER"]),
        plot_dropped_employee_size=float(resolved["PLOT_DROPPED_EMPLOYEE_SIZE"]),
        plot_dropped_employee_label=str(resolved["PLOT_DROPPED_EMPLOYEE_LABEL"]),
        plot_node_label_offset=tuple(resolved["PLOT_NODE_LABEL_OFFSET"]),
        plot_small_label_fontsize=int(resolved["PLOT_SMALL_LABEL_FONTSIZE"]),
        plot_employee_id_label_offset=tuple(resolved["PLOT_EMPLOYEE_ID_LABEL_OFFSET"]),
        plot_employee_id_label_color=str(resolved["PLOT_EMPLOYEE_ID_LABEL_COLOR"]),
        plot_visit_order_label_offset=tuple(resolved["PLOT_VISIT_ORDER_LABEL_OFFSET"]),
        plot_x_label=str(resolved["PLOT_XLABEL"]),
        plot_y_label=str(resolved["PLOT_YLABEL"]),
        plot_grid_line_style=str(resolved["PLOT_GRID_LINESTYLE"]),
        plot_grid_alpha=float(resolved["PLOT_GRID_ALPHA"]),
        plot_legend_loc=str(resolved["PLOT_LEGEND_LOC"]),
        plot_legend_bbox_to_anchor=tuple(resolved["PLOT_LEGEND_BBOX_TO_ANCHOR"]),
        plot_legend_border_axes_pad=float(resolved["PLOT_LEGEND_BORDERAXESPAD"]),
        plot_route_color=str(resolved["PLOT_ROUTE_COLOR"]),
        plot_route_line_width=float(resolved["PLOT_ROUTE_LINE_WIDTH"]),
        plot_route_point_size=float(resolved["PLOT_ROUTE_POINT_SIZE"]),
        plot_empty_route_line_style=(
            None if resolved["PLOT_EMPTY_ROUTE_LINESTYLE"] is None else tuple(resolved["PLOT_EMPTY_ROUTE_LINESTYLE"])
        ),
        plot_empty_route_label=str(resolved["PLOT_EMPTY_ROUTE_LABEL"]),
        plot_leg_both_counted_line_style=str(resolved["PLOT_LEG_BOTH_COUNTED_LINESTYLE"]),
        plot_leg_mixed_counted_line_style=str(resolved["PLOT_LEG_MIXED_COUNTED_LINESTYLE"]),
        plot_leg_not_counted_line_style=str(resolved["PLOT_LEG_NOT_COUNTED_LINESTYLE"]),
    )
    return settings
