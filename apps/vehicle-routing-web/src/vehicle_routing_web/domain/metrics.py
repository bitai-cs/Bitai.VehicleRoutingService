"""Derived dashboard metrics: values not present in the solver response as such.

Everything here is computed from the response only (no payload needed) and
follows the reference ``write_operational_kpis_csv`` formulas. Balance
statistics use **active routes only** (routes with at least one serviced
stop) so unused vehicles do not distort them. Metrics whose denominator is
zero are ``None`` rather than a made-up number.
"""

from __future__ import annotations

from dataclasses import dataclass

from vehicle_routing_web.domain.solve_response import SolvedRoute, SolveResponse
from vehicle_routing_web.domain.stats import coefficient_of_variation, mean, percentile


@dataclass(frozen=True, slots=True)
class DerivedMetrics:
    routes_total: int
    routes_active: int
    routes_empty: int
    served: int
    omitted: int
    total_employees: int
    mean_demand_utilization_pct: float
    p95_demand_utilization_pct: float
    duration_balance_cv: float
    service_stops_balance_cv: float
    max_min_duration_ratio: float | None
    productive_time_share_pct: float
    avg_distance_per_served_km: float
    avg_time_per_served_min: float
    total_uncosted_distance_km: float
    total_modeled_duration_min: float
    deadhead_ratio_pct: float | None
    co2_per_served_employee_kg: float | None
    unattributed_cost_share: float | None


def active_routes(response: SolveResponse) -> list[SolvedRoute]:
    return [route for route in response.solved_routes if not route.is_empty_route]


def compute_metrics(response: SolveResponse) -> DerivedMetrics:
    routes = response.solved_routes
    active = active_routes(response)
    served = response.total_covered_service_points
    omitted = len(response.omitted_service_points)

    durations = [float(r.modeled_route_duration) for r in active]
    stops = [float(r.total_service_stops) for r in active]
    utilizations = [r.demand_utilization_pct for r in active]

    total_duration = sum(durations)
    productive = sum(float(r.productive_time_min) for r in active)
    physical = sum(r.physical_route_distance for r in active)

    ratio = max(durations) / min(durations) if durations and min(durations) > 0 else None
    total_physical = response.total_physical_route_distance
    objective = response.total_objective_value

    return DerivedMetrics(
        routes_total=len(routes),
        routes_active=len(active),
        routes_empty=len(routes) - len(active),
        served=served,
        omitted=omitted,
        total_employees=served + omitted,
        mean_demand_utilization_pct=mean(utilizations),
        p95_demand_utilization_pct=percentile(utilizations, 0.95),
        duration_balance_cv=coefficient_of_variation(durations),
        service_stops_balance_cv=coefficient_of_variation(stops),
        max_min_duration_ratio=ratio,
        productive_time_share_pct=(productive / total_duration * 100.0) if total_duration > 0 else 0.0,
        avg_distance_per_served_km=(physical / served) if served > 0 else 0.0,
        avg_time_per_served_min=(total_duration / served) if served > 0 else 0.0,
        total_uncosted_distance_km=sum(r.uncosted_distance_km for r in active),
        total_modeled_duration_min=total_duration,
        deadhead_ratio_pct=(response.deadhead_distance_km / total_physical * 100.0) if total_physical > 0 else None,
        co2_per_served_employee_kg=(response.estimated_co2_kg / served) if served > 0 else None,
        unattributed_cost_share=(response.objective_unattributed_cost / objective) if objective > 0 else None,
    )
