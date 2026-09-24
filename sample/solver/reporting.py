import csv
import os
from math import sqrt
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import Settings
from scenario import Scenario
from solver import SolveResult

# Internal reporting policy:
# - CSV outputs must reflect operational meaning, not internal solver implementation details.
# - Route and stop metrics must respect business semantics (for example, whether the first/last leg
#   is counted according to UCMSME_COUNT_FIRST_LEG_COST and UCMSME_COUNT_LAST_LEG_COST), and they
#   must not mix physical values with modeled values.
# - solution-summary is an executive summary and should contain the key aggregates, but it must not
#   include a second KPI_status_flags block or a level of analysis that duplicates the KPI report.
# - operational-kpis owns the business-oriented KPI grouping and the operational interpretation of
#   service performance; it is not a traffic-light dashboard and it does not assign green/amber/red
#   labels to every metric.
# - omitted_employees has its own dedicated CSV and must not be embedded inside the summary.
# - Column naming must remain in English and use business language: route, stop, service,
#   remaining_time_to_limit_min, service_time_min, etc. Internal optimizer variable names must not
#   be exposed in end-user reports.


def ensure_output_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _leg_linestyle(settings: Settings, count_cost: bool, count_time: bool) -> str:
    if count_cost and count_time:
        return settings.plot_leg_both_counted_line_style
    if count_cost != count_time:
        return settings.plot_leg_mixed_counted_line_style
    return settings.plot_leg_not_counted_line_style


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


def _mean(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _stddev_population(values: list[float]) -> float:
    if not values:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return sqrt(variance)


def _coefficient_of_variation(values: list[float]) -> float:
    mean_value = _mean(values)
    if mean_value == 0:
        return 0.0
    return _stddev_population(values) / mean_value


def _write_aggregate_rows(
    writer: Any,
    label: str,
    values: list[float],
    decimals: int = 3,
    metric_description: str = "",
) -> None:
    description = metric_description or f"Route-level aggregate metric for {label}."
    writer.writerow([
        f"{label}_avg",
        f"{_mean(values):.{decimals}f}",
        f"Average value of {description.lower()}",
        "Mean across all solved routes.",
    ])
    writer.writerow([
        f"{label}_p95",
        f"{_percentile(values, 0.95):.{decimals}f}",
        f"95th percentile value of {description.lower()}",
        "Percentile 95 across all solved routes.",
    ])
    writer.writerow([
        f"{label}_min",
        f"{(min(values) if values else 0.0):.{decimals}f}",
        f"Minimum value of {description.lower()}",
        "Minimum across all solved routes.",
    ])
    writer.writerow([
        f"{label}_max",
        f"{(max(values) if values else 0.0):.{decimals}f}",
        f"Maximum value of {description.lower()}",
        "Maximum across all solved routes.",
    ])


def _semaphore_high_is_good(value: float, green_min: float, amber_min: float) -> str:
    if value >= green_min:
        return "GREEN"
    if value >= amber_min:
        return "AMBER"
    return "RED"


def _semaphore_low_is_good(value: float, green_max: float, amber_max: float) -> str:
    if value <= green_max:
        return "GREEN"
    if value <= amber_max:
        return "AMBER"
    return "RED"


def _semaphore_mid_band_is_good(value: float, green_min: float, green_max: float, amber_min: float, amber_max: float) -> str:
    if green_min <= value <= green_max:
        return "GREEN"
    if amber_min <= value <= amber_max:
        return "AMBER"
    return "RED"


def plot_scenario(settings: Settings, scenario: Scenario) -> None:
    ensure_output_dir(settings.output_dir)
    file_path = os.path.join(settings.output_dir, settings.scenario_plot_filename)
    plt.figure(figsize=settings.plot_figsize)
    plt.scatter(
        [scenario.coord_by_node[n][0] for n in scenario.employee_nodes],
        [scenario.coord_by_node[n][1] for n in scenario.employee_nodes],
        marker=settings.plot_employee_marker,
        s=settings.plot_employee_size,
        c=settings.plot_employee_color,
        alpha=settings.plot_employee_alpha,
        label=settings.plot_employee_label,
    )
    plt.scatter(
        [scenario.coord_by_node[n][0] for n in range(scenario.number_of_initial_route_coords)],
        [scenario.coord_by_node[n][1] for n in range(scenario.number_of_initial_route_coords)],
        marker=settings.plot_initial_marker,
        s=settings.plot_initial_size,
        c=settings.plot_initial_color,
        label=settings.plot_initial_label,
    )
    plt.scatter(
        [scenario.coord_by_node[n][0] for n in range(scenario.number_of_initial_route_coords, scenario.number_of_initial_route_coords + scenario.number_of_final_route_coords)],
        [scenario.coord_by_node[n][1] for n in range(scenario.number_of_initial_route_coords, scenario.number_of_initial_route_coords + scenario.number_of_final_route_coords)],
        marker=settings.plot_final_marker,
        s=settings.plot_final_size,
        c=settings.plot_final_color,
        label=settings.plot_final_label,
    )
    for node, label in scenario.label_by_node.items():
        x, y = scenario.coord_by_node[node]
        if node < scenario.employee_node_offset:
            plt.annotate(label, (x, y), xytext=settings.plot_node_label_offset, textcoords="offset points")
        else:
            plt.annotate(
                label,
                (x, y),
                xytext=settings.plot_employee_id_label_offset,
                textcoords="offset points",
                fontsize=settings.plot_small_label_fontsize,
                color=settings.plot_employee_id_label_color,
            )
    plt.title("VRP demo")
    plt.xlabel(settings.plot_x_label)
    plt.ylabel(settings.plot_y_label)
    plt.grid(True, linestyle=settings.plot_grid_line_style, alpha=settings.plot_grid_alpha)
    plt.xlim(settings.area_min_x, settings.area_max_x)
    plt.ylim(settings.area_min_y, settings.area_max_y)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.legend(loc=settings.plot_legend_loc, bbox_to_anchor=settings.plot_legend_bbox_to_anchor, borderaxespad=settings.plot_legend_border_axes_pad)
    plt.tight_layout()
    plt.savefig(file_path, dpi=settings.plot_dpi, bbox_inches=settings.plot_savefig_bbox)
    plt.close()
    print(f"Scenario saved to: {file_path}")


def plot_vehicle_route(settings: Settings, scenario: Scenario, vehicle_id: int, route_nodes: list[int], dropped_employees: list[int]) -> None:
    ensure_output_dir(settings.output_dir)
    file_name = settings.route_plot_filename_template.format(vehicle=vehicle_id)
    file_path = os.path.join(settings.output_dir, file_name)
    plt.figure(figsize=settings.plot_figsize)
    plt.scatter(
        [scenario.coord_by_node[n][0] for n in scenario.employee_nodes],
        [scenario.coord_by_node[n][1] for n in scenario.employee_nodes],
        marker=settings.plot_employee_marker,
        s=settings.plot_employee_size,
        c=settings.plot_employee_color,
        alpha=settings.plot_employee_alpha,
        label=settings.plot_employee_label,
    )
    if dropped_employees:
        plt.scatter(
            [scenario.coord_by_node[n][0] for n in dropped_employees],
            [scenario.coord_by_node[n][1] for n in dropped_employees],
            marker=settings.plot_dropped_employee_marker,
            s=settings.plot_dropped_employee_size,
            c=settings.plot_dropped_employee_color,
            alpha=settings.plot_employee_alpha,
            label=settings.plot_dropped_employee_label,
        )
    rx = [scenario.coord_by_node[n][0] for n in route_nodes]
    ry = [scenario.coord_by_node[n][1] for n in route_nodes]
    if len(route_nodes) <= 2:
        plt.plot(rx, ry, color=settings.plot_route_color, linewidth=settings.plot_route_line_width, linestyle=settings.plot_empty_route_line_style)
        plt.plot([], [], color=settings.plot_route_color, linewidth=settings.plot_route_line_width, linestyle=settings.plot_empty_route_line_style, label=settings.plot_empty_route_label)
    else:
        for idx in range(len(route_nodes) - 1):
            if idx == 0:
                linestyle = _leg_linestyle(settings, settings.count_first_leg_cost[vehicle_id], settings.count_first_leg_time[vehicle_id])
            elif idx == len(route_nodes) - 2:
                linestyle = _leg_linestyle(settings, settings.count_last_leg_cost[vehicle_id], settings.count_last_leg_time[vehicle_id])
            else:
                linestyle = "solid"
            plt.plot(rx[idx:idx + 2], ry[idx:idx + 2], color=settings.plot_route_color, linewidth=settings.plot_route_line_width, linestyle=linestyle)
        plt.plot([], [], color=settings.plot_route_color, linewidth=settings.plot_route_line_width, linestyle="solid", label=f"Vehicle route {vehicle_id}")
    plt.scatter(rx, ry, c=settings.plot_route_color, s=settings.plot_route_point_size)
    for order, node in enumerate(route_nodes):
        x, y = scenario.coord_by_node[node]
        plt.annotate(str(order), (x, y), xytext=settings.plot_visit_order_label_offset, textcoords="offset points", fontsize=settings.plot_small_label_fontsize)
        if node >= scenario.employee_node_offset:
            plt.annotate(
                scenario.label_by_node[node],
                (x, y),
                xytext=settings.plot_employee_id_label_offset,
                textcoords="offset points",
                fontsize=settings.plot_small_label_fontsize,
                color=settings.plot_employee_id_label_color,
            )
    plt.title(f"Vehicle {vehicle_id} route")
    plt.xlabel(settings.plot_x_label)
    plt.ylabel(settings.plot_y_label)
    plt.grid(True, linestyle=settings.plot_grid_line_style, alpha=settings.plot_grid_alpha)
    plt.xlim(settings.area_min_x, settings.area_max_x)
    plt.ylim(settings.area_min_y, settings.area_max_y)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.legend(loc=settings.plot_legend_loc, bbox_to_anchor=settings.plot_legend_bbox_to_anchor, borderaxespad=settings.plot_legend_border_axes_pad)
    plt.tight_layout()
    plt.savefig(file_path, dpi=settings.plot_dpi, bbox_inches=settings.plot_savefig_bbox)
    plt.close()
    print(f"Route saved to: {file_path}")


def write_route_details_csv(settings: Settings, solve_result: SolveResult) -> None:
    # Route report policy:
    # This file must be the operational view of each route. It must not mirror the solver's internal
    # structure or include raw metrics without business translation. Any reported distance/time column
    # must have been calculated using the active business logic (for example, whether the first/last
    # leg is counted based on the environment configuration).
    ensure_output_dir(settings.output_dir)
    csv_path = os.path.join(settings.output_dir, settings.route_details_csv_filename)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "vehicle_id",
            "origin",
            "destination",
            "employees_served",
            "vehicle_capacity",
            "demand_utilization_pct",
            "departure_time",
            "arrival_time",
            "time_limit",
            "start_delay_window_min",
            "remaining_time_to_limit_min",
            "modeled_duration_min",
            "drive_time_min",
            "wait_time_min",
            "service_time_min",
            "productive_time_min",
            "idle_ratio_pct",
            "drive_time_pct",
            "service_time_pct",
            "wait_time_pct",
            "accounted_distance_km",
            "physical_distance_km",
            "distance_efficiency_ratio",
            "uncosted_distance_km",
            "route_objective_contribution",
            "total_stops",
            "total_service_stops",
            "is_empty_route",
            "first_service_arrival",
            "last_service_arrival",
            "priority_low_served",
            "priority_medium_served",
            "priority_high_served",
            "route_path",
        ])
        for route in solve_result.solved_routes:
            writer.writerow([
                route.vehicle_id,
                route.start_node_label,
                route.end_node_label,
                route.covered_demand,
                route.maximum_demand_coverage,
                f"{route.demand_utilization_pct:.2f}",
                route.departure_time,
                route.arrival_time,
                route.arrival_time_limit,
                route.start_delay_from_window_min,
                route.remaining_time_to_limit_min,
                route.modeled_route_duration,
                route.total_drive_time_min,
                route.total_wait_time_min,
                route.total_service_time_min,
                route.productive_time_min,
                f"{route.idle_ratio_pct:.2f}",
                f"{route.drive_time_pct:.2f}",
                f"{route.service_time_pct:.2f}",
                f"{route.wait_time_pct:.2f}",
                f"{route.modeled_route_distance:.3f}",
                f"{route.physical_route_distance:.3f}",
                f"{route.distance_efficiency_ratio:.6f}",
                f"{route.uncosted_distance_km:.3f}",
                route.route_objective_contribution,
                route.total_stops,
                route.total_service_stops,
                route.is_empty_route,
                route.first_service_arrival,
                route.last_service_arrival,
                route.priority_low_served,
                route.priority_medium_served,
                route.priority_high_served,
                " -> ".join(f"{stop.node_id}({stop.arrival_time})" for stop in route.stops),
            ])
    print(f"Route details saved to: {csv_path}")


def write_stop_details_csv(settings: Settings, solve_result: SolveResult) -> None:
    # Stop report policy:
    # This CSV describes the route step by step from the operational execution point of view. It
    # exposes leg distances, travel times, wait/service times, and cumulative values, but always using
    # the same semantics as the rest of the reports: business values, not internals of the optimization
    # model.
    ensure_output_dir(settings.output_dir)
    csv_path = os.path.join(settings.output_dir, settings.route_stop_details_csv_filename)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "vehicle_id",
            "route_start_label",
            "route_end_label",
            "stop_sequence",
            "stop_type",
            "node_id",
            "node_label",
            "arrival_minutes",
            "arrival_time",
            "duration_from_previous_arrival_minutes",
            "cumulative_duration_from_previous_arrival_minutes",
            "departure_minutes",
            "departure_time",
            "service_minutes",
            "wait_minutes",
            "cumulative_wait_minutes",
            "load_before",
            "load_delta",
            "load_after",
            "leg_distance_km_from_prev",
            "leg_travel_minutes_from_prev",
            "cumulative_distance_km",
        ])
        for route in solve_result.solved_routes:
            previous_arrival_minutes: int | None = None
            cumulative_duration_from_previous_arrival_minutes = 0
            for stop in route.stops:
                if previous_arrival_minutes is None:
                    duration_from_previous_arrival_minutes = 0
                else:
                    duration_from_previous_arrival_minutes = stop.arrival_minutes - previous_arrival_minutes
                cumulative_duration_from_previous_arrival_minutes += duration_from_previous_arrival_minutes
                previous_arrival_minutes = stop.arrival_minutes

                writer.writerow([
                    route.vehicle_id,
                    route.start_node_label,
                    route.end_node_label,
                    stop.stop_sequence,
                    stop.stop_type,
                    stop.node_id,
                    stop.node_label,
                    stop.arrival_minutes,
                    stop.arrival_time,
                    duration_from_previous_arrival_minutes,
                    cumulative_duration_from_previous_arrival_minutes,
                    stop.departure_minutes,
                    stop.departure_time,
                    stop.service_minutes,
                    stop.wait_minutes,
                    stop.cumulative_wait_minutes,
                    stop.load_before,
                    stop.load_delta,
                    stop.load_after,
                    f"{stop.leg_distance_km_from_prev:.3f}",
                    stop.leg_travel_minutes_from_prev,
                    f"{stop.cumulative_distance_km:.3f}",
                ])
    print(f"Stop details saved to: {csv_path}")


def write_solution_summary_csv(settings: Settings, solve_result: SolveResult, scenario: Scenario) -> None:
    # Executive summary policy:
    # This file should act as a high-level operational snapshot with only global values and counts.
    # Combined metrics, statistical analysis, and route-balance diagnostics belong to
    # operational-kpis.csv.
    ensure_output_dir(settings.output_dir)
    csv_path = os.path.join(settings.output_dir, settings.solution_summary_csv_filename)
    routes = solve_result.solved_routes
    routes_generated_total = len(routes)
    empty_routes_total = sum(1 for route in routes if route.is_empty_route)
    active_routes_total = routes_generated_total - empty_routes_total
    total_stops_all_routes = sum(route.total_stops for route in routes)
    total_service_stops_all_routes = sum(route.total_service_stops for route in routes)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["**SUMMARY**", "", "", ""])

        def write_summary_metric(field: str, value: object, description: str, calculation: str) -> None:
            writer.writerow([field, value, description, calculation])

        write_summary_metric("status", solve_result.status, "Final solver feasibility status.", "Direct value from OR-Tools solve status.")
        write_summary_metric("total_objective_value", solve_result.total_objective_value, "Final objective value for the selected solution.", "Directly read from solution.ObjectiveValue().")
        write_summary_metric("search_time_ms", solve_result.search_wall_time_ms, "Wall-clock search time in milliseconds.", "Directly reported by solver wall time counter.")
        write_summary_metric("total_employees", settings.number_of_employees, "Total number of employees in scenario demand.", "Input configuration value from settings.")
        write_summary_metric("served_employees_total", solve_result.total_covered_service_points, "Total employees served by all routes.", "Sum of covered demand across solved routes.")
        write_summary_metric("omitted_employees_total", len(solve_result.omitted_service_points), "Total employees not served.", "Count of omitted service points in solve result.")
        write_summary_metric("routes_generated_total", routes_generated_total, "Total routes generated by the solver.", "Count of solve_result.solved_routes entries.")
        write_summary_metric("active_routes_total", active_routes_total, "Routes with at least one serviced stop.", "routes_generated_total - empty_routes_total.")
        write_summary_metric("empty_routes_total", empty_routes_total, "Routes with zero serviced stops.", "Count of routes where is_empty_route=True.")
        write_summary_metric("total_stops_all_routes", total_stops_all_routes, "Total stop records across all generated routes.", "Sum of route.total_stops across routes.")
        write_summary_metric("total_service_stops_all_routes", total_service_stops_all_routes, "Total serviced stops across all generated routes.", "Sum of route.total_service_stops across routes.")
        write_summary_metric("accounted_distance_total_km", f"{solve_result.total_modeled_route_distance:.3f}", "Distance counted by configured modeling rules (km).", "Sum of modeled route distance (includes/excludes extreme legs by COUNT_FIRST/LAST_LEG_COST flags).")
        write_summary_metric("physical_distance_total_km", f"{solve_result.total_physical_route_distance:.3f}", "Real traveled distance across all arcs (km).", "Sum of physical arc distances for all solved routes.")
        write_summary_metric("deadhead_distance_km", f"{solve_result.deadhead_distance_km:.3f}", "Distance on start/end repositioning legs (km).", "Sum of physical arc distances where arc leaves START or reaches END.")
        write_summary_metric("total_drive_min", solve_result.total_drive_min, "Total driving minutes.", "Sum of reported leg travel time across routes.")
        write_summary_metric("total_wait_min", solve_result.total_wait_min, "Total waiting minutes.", "Sum of route waiting time from schedule slack.")
        write_summary_metric("total_service_min", solve_result.total_service_min, "Total service minutes at employee stops.", "Sum of service lag minutes across all routes.")
        write_summary_metric("omitted_low_priority_count", solve_result.omitted_low_priority_count, "Number of omitted low-priority employees.", "Count omitted service points with LOW priority.")
        write_summary_metric("omitted_medium_priority_count", solve_result.omitted_medium_priority_count, "Number of omitted medium-priority employees.", "Count omitted service points with MEDIUM priority.")
        write_summary_metric("omitted_high_priority_count", solve_result.omitted_high_priority_count, "Number of omitted high-priority employees.", "Count omitted service points with HIGH priority.")
        write_summary_metric("solver_status_detail", solve_result.solver_status_detail, "Detailed solver status.", "Mapped solver status name.")
        write_summary_metric("solver_branches", solve_result.solver_branches, "Branching decisions explored by the solver.", "Direct branch counter from OR-Tools.")
        write_summary_metric("solver_failures", solve_result.solver_failures, "Failed nodes/backtracks during search.", "Direct failure counter from OR-Tools.")
    print(f"Solution summary saved to: {csv_path}")


def write_omitted_employees_csv(settings: Settings, solve_result: SolveResult, scenario: Scenario) -> None:
    # Omitted employees policy:
    # The list of unserved employees must be written to a separate CSV. It must not appear nested in
    # the summary or mixed with operational KPIs. This separation keeps the executive summary clean and
    # preserves the exclusion detail with its own spatial and priority context.
    ensure_output_dir(settings.output_dir)
    csv_path = os.path.join(settings.output_dir, settings.omitted_employees_csv_filename)
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["employee_id", "priority", "reference_distance_km", "x_km", "y_km"])
        for employee_id in solve_result.omitted_service_points:
            x, y = scenario.coord_by_node[employee_id]
            reference_distance_km = ((x - scenario.employee_priority_reference_coordinate[0]) ** 2 + (y - scenario.employee_priority_reference_coordinate[1]) ** 2) ** 0.5
            writer.writerow([
                employee_id,
                scenario.priority_by_employee[employee_id],
                f"{reference_distance_km:.3f}",
                x,
                y,
            ])
    print(f"Omitted employees saved to: {csv_path}")


def write_operational_kpis_csv(settings: Settings, solve_result: SolveResult) -> None:
    # Operational KPI policy:
    # This file owns the business-oriented KPI grouping and the performance interpretation. Each KPI
    # carries an informative target but no status classification. Balance metrics are computed over
    # active routes only, so unused vehicles do not distort them. The summary must not repeat this
    # block; it should focus on the executive output rather than the detailed operational control.
    ensure_output_dir(settings.output_dir)
    csv_path = os.path.join(settings.output_dir, settings.operational_kpis_csv_filename)
    routes = solve_result.solved_routes
    operational_routes = [route for route in routes if not route.is_empty_route]

    vehicles_total = len(routes)
    vehicles_used = len(operational_routes)
    fleet_utilization_pct = (vehicles_used / vehicles_total * 100.0) if vehicles_total > 0 else 0.0

    served_employees = solve_result.total_covered_service_points
    omitted_employees = len(solve_result.omitted_service_points)
    total_employees = served_employees + omitted_employees
    service_level_pct = (served_employees / total_employees * 100.0) if total_employees > 0 else 0.0

    durations = [float(route.modeled_route_duration) for route in operational_routes]
    demands = [float(route.covered_demand) for route in operational_routes]
    service_stops = [float(route.total_service_stops) for route in operational_routes]
    demand_utilizations = [route.demand_utilization_pct for route in operational_routes]
    productive_times = [float(route.productive_time_min) for route in operational_routes]
    physical_distances = [route.physical_route_distance for route in operational_routes]

    service_stop_waits = [
        float(stop.wait_minutes)
        for route in operational_routes
        for stop in route.stops
        if stop.stop_type == "SERVICE"
    ]

    total_modeled_duration = sum(durations)
    total_productive_time = sum(productive_times)
    productive_time_share_pct = (total_productive_time / total_modeled_duration * 100.0) if total_modeled_duration > 0 else 0.0

    operational_physical_distance_km = sum(physical_distances)

    avg_distance_per_served_employee_km = (
        operational_physical_distance_km / served_employees if served_employees > 0 else 0.0
    )
    avg_time_per_served_employee_min = (total_modeled_duration / served_employees) if served_employees > 0 else 0.0
    total_uncosted_distance_km = sum(route.uncosted_distance_km for route in operational_routes)

    max_min_duration_ratio: float | None = None
    if durations and min(durations) > 0:
        max_min_duration_ratio = max(durations) / min(durations)

    max_route_duration_min = max(durations) if durations else 0.0
    min_route_duration_min = min(durations) if durations else 0.0
    spread_route_duration_min = max_route_duration_min - min_route_duration_min

    workload_balance_demand_std = _stddev_population(demands)
    workload_balance_distance_std = _stddev_population(physical_distances)
    workload_balance_duration_std = _stddev_population(durations)

    average_stop_wait_min = _mean(service_stop_waits)
    p95_stop_wait_min = _percentile(service_stop_waits, 0.95)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "metric", "value", "target", "interpretation"])

        mean_demand_utilization = _mean(demand_utilizations)
        p95_demand_utilization = _percentile(demand_utilizations, 0.95)
        duration_balance_cv = _coefficient_of_variation(durations)
        service_stops_balance_cv = _coefficient_of_variation(service_stops)

        def add_kpi(section: str, metric: str, value: object, target: str, interpretation: str) -> None:
            writer.writerow([section, metric, value, target, interpretation])

        add_kpi(
            "coverage_and_service",
            "service_level_pct",
            f"{service_level_pct:.2f}%",
            ">= 95%",
            "Share of employees served relative to total demand. This is the primary service coverage metric.",
        )
        add_kpi(
            "coverage_and_service",
            "weighted_service_level_pct",
            f"{solve_result.weighted_service_level_pct:.2f}%",
            ">= 97%",
            "Priority-weighted service coverage. It reflects whether the most critical demand is being served.",
        )
        add_kpi(
            "coverage_and_service",
            "employees_served",
            served_employees,
            "as high as possible",
            "Count of employees successfully covered by the solved routes.",
        )
        add_kpi(
            "coverage_and_service",
            "employees_omitted",
            omitted_employees,
            "0 preferred",
            "Count of employees left unserved. This should be minimized in a feasible plan.",
        )

        add_kpi(
            "efficiency",
            "avg_distance_per_served_employee_km",
            f"{avg_distance_per_served_employee_km:.3f}",
            "<= 20 km preferred",
            "Average physical distance per served employee. Lower values indicate tighter geographic efficiency.",
        )
        add_kpi(
            "efficiency",
            "avg_time_per_served_employee_min",
            f"{avg_time_per_served_employee_min:.2f}",
            "<= 20 min preferred",
            "Average modeled time per served employee. Useful for comparing effort per worker served.",
        )
        add_kpi(
            "efficiency",
            "productive_time_share_pct",
            f"{productive_time_share_pct:.2f}%",
            ">= 80% preferred",
            "Share of modeled route time spent in productive activity (drive + service), versus waiting or slack.",
        )
        add_kpi(
            "efficiency",
            "total_uncosted_distance_km",
            f"{total_uncosted_distance_km:.3f}",
            "as low as possible",
            "Distance outside the objective cost logic. This helps reveal travel that is not fully captured by the scoring model.",
        )

        add_kpi(
            "load_balance_and_fleet",
            "fleet_vehicles_total",
            vehicles_total,
            "scenario-defined",
            "Total vehicles available for the current scenario.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "fleet_vehicles_used",
            vehicles_used,
            "as needed",
            "Number of routes that are actually active in the solution.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "fleet_utilization_pct",
            f"{fleet_utilization_pct:.2f}%",
            "60%-90% preferred",
            "Share of the available fleet that is actively used. Good utilization reduces idle capacity without overstretching the fleet.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "avg_demand_utilization_pct",
            f"{mean_demand_utilization:.2f}%",
            "60%-85% preferred",
            "Average demand utilization across routes. Values near saturation indicate heavy consolidation but increased risk of tight routing.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "p95_demand_utilization_pct",
            f"{p95_demand_utilization:.2f}%",
            "<= 100% preferred",
            "P95 demand utilization across routes. This identifies the most stressed routes in the plan.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "duration_balance_cv",
            f"{duration_balance_cv:.6f}",
            "<= 0.50 preferred",
            "Coefficient of variation for route durations. Lower values indicate more balanced route load across vehicles.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "service_stops_balance_cv",
            f"{service_stops_balance_cv:.6f}",
            "<= 0.50 preferred",
            "Coefficient of variation for serviced stops per route. Lower values indicate more uniform stop distribution.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "workload_balance_demand_std",
            f"{workload_balance_demand_std:.6f}",
            "as low as possible",
            "Population standard deviation of covered demand across active routes. In plain terms, it shows how evenly employee load is distributed among vehicles: lower values mean routes carry similar demand, which is usually preferred because it reduces overload risk on specific vehicles and improves operational fairness. Higher values indicate that a few routes are carrying much more demand than others, which can increase service fragility and make day-to-day operations less predictable. Example: a value near 0.89 is better than 1.50 or 2.00 because demand is less dispersed, so assignment pressure is more uniform across vehicles.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "workload_balance_distance_std",
            f"{workload_balance_distance_std:.6f}",
            "as low as possible",
            "Population standard deviation of physical route distance across active routes. In practical terms, it measures how different route lengths are from one vehicle to another: lower values are typically recommended because they imply a more even split of travel effort, fuel consumption, and driver fatigue. Higher values suggest that some vehicles are traveling significantly farther than others, which can raise operating costs and create uneven workload pressure. Example: if this KPI is 17.33 km, it is better than 25 km because the distance spread between routes is smaller, so the fleet operates with lower imbalance and less extreme long-route burden.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "workload_balance_duration_std",
            f"{workload_balance_duration_std:.6f}",
            "as low as possible",
            "Population standard deviation of modeled route duration across active routes. Put simply, it indicates how balanced route times are across the fleet: lower values are generally better because they mean drivers finish in similar time windows, simplifying supervision, shift planning, and SLA compliance. Higher values mean some routes take much longer than others, which can lead to overtime, harder dispatch coordination, and lower perceived service consistency. Example: a duration std of 17.35 min is better than 25 min because completion times are less spread out, reducing overtime risk and improving shift synchronization.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "max_route_duration_min",
            f"{max_route_duration_min:.2f}",
            "as low as possible",
            "Maximum modeled route duration among active routes.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "min_route_duration_min",
            f"{min_route_duration_min:.2f}",
            "as high as possible",
            "Minimum modeled route duration among active routes.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "spread_route_duration_min",
            f"{spread_route_duration_min:.2f}",
            "as low as possible",
            "Difference between the longest and shortest active-route durations.",
        )
        add_kpi(
            "load_balance_and_fleet",
            "max_min_duration_ratio",
            f"{max_min_duration_ratio:.6f}" if max_min_duration_ratio is not None else "None",
            "close to 1.0 preferred",
            "Max/min duration ratio across routes. A high value means uneven routing effort among vehicles.",
        )

        add_kpi(
            "risk_and_exceptions",
            "average_stop_wait_min",
            f"{average_stop_wait_min:.3f}",
            "<= 5 min preferred",
            "Average waiting time at stops. Higher values indicate operational friction or schedule slack.",
        )
        add_kpi(
            "risk_and_exceptions",
            "p95_stop_wait_min",
            f"{p95_stop_wait_min:.3f}",
            "<= 15 min preferred",
            "95th percentile of waiting time at service stops to highlight peak-delay risk.",
        )
        add_kpi(
            "sustainability",
            "co2_kg_per_km",
            f"{solve_result.co2_kg_per_km:.6f}",
            "scenario-defined",
            "CO2 factor used for estimation (kg per km).",
        )
        add_kpi(
            "sustainability",
            "estimated_co2_kg",
            f"{solve_result.estimated_co2_kg:.3f}",
            "as low as possible",
            "Estimated total CO2 emissions.",
        )
        add_kpi(
            "objective_diagnostics",
            "objective_travel_cost",
            solve_result.objective_travel_cost,
            "contextual",
            "Objective contribution from travel arcs.",
        )
        add_kpi(
            "objective_diagnostics",
            "objective_omission_penalty",
            solve_result.objective_omission_penalty,
            "contextual",
            "Objective contribution from omitted employees.",
        )
        add_kpi(
            "objective_diagnostics",
            "objective_unattributed_cost",
            solve_result.objective_unattributed_cost,
            "close to 0 preferred",
            "Objective remainder not explained by travel and omission terms.",
        )
        add_kpi(
            "objective_diagnostics",
            "solver_branches",
            solve_result.solver_branches,
            "contextual",
            "Branching decisions explored by the solver.",
        )
        add_kpi(
            "objective_diagnostics",
            "solver_failures",
            solve_result.solver_failures,
            "contextual",
            "Backtracks/failures reported during search.",
        )

    print(f"Operational KPIs saved to: {csv_path}")


def write_all_outputs(settings: Settings, scenario: Scenario, solve_result: SolveResult) -> None:
    # Output-set policy:
    # Helper artifacts such as plots are written first, then the detailed reports, and finally the
    # business CSV files: route details, stop details, omitted employees, solution summary, and
    # operational KPIs. Each file has a clear responsibility and does not duplicate the same data in a
    # different format or with the same semantics in multiple places.
    if settings.plot_scenario:
        plot_scenario(settings, scenario)
    if settings.plot_all_routes:
        for route in solve_result.solved_routes:
            route_nodes = [stop.node_id for stop in route.stops]
            plot_vehicle_route(settings, scenario, route.vehicle_id, route_nodes, solve_result.omitted_service_points)
    write_route_details_csv(settings, solve_result)
    write_stop_details_csv(settings, solve_result)
    write_omitted_employees_csv(settings, solve_result, scenario)
    write_solution_summary_csv(settings, solve_result, scenario)
    write_operational_kpis_csv(settings, solve_result)
