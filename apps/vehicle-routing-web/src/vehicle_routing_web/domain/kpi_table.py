"""Comprehensive KPI table (spec tab 8): rows with target text and a rating.

Only metrics with an explicit numeric target in the specification or the
reference report get a rating; the rest are ``Rating.INFO``. Values that
cannot be computed are ``None`` and shown as "not available".
"""

from __future__ import annotations

from dataclasses import dataclass

from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.domain.solution import Solution
from vehicle_routing_web.domain.thresholds import Rating

SECTION_TITLES: dict[str, str] = {
    "coverage": "Coverage & service",
    "efficiency": "Efficiency",
    "fleet": "Load balance & fleet",
    "risk": "Risk & exceptions",
    "sustainability": "Sustainability",
    "objective": "Objective diagnostics",
}


@dataclass(frozen=True, slots=True)
class KpiRow:
    section: str
    metric: str
    value: float | int | None
    unit: str
    target: str
    rating: Rating
    interpretation: str


def build_kpi_rows(solution: Solution) -> list[KpiRow]:
    r = solution.response
    m = solution.metrics
    rows: list[KpiRow] = []

    def add(
        section: str,
        metric: str,
        value: float | int | None,
        unit: str,
        target: str,
        rating: Rating,
        interpretation: str,
    ) -> None:
        rows.append(KpiRow(section, metric, value, unit, target, rating, interpretation))

    info = Rating.INFO

    add(
        "coverage",
        "service_level_pct",
        r.service_level_pct,
        "%",
        ">= 95%",
        t.service_level_rating(r.service_level_pct),
        "Share of employees served relative to total demand.",
    )
    add(
        "coverage",
        "weighted_service_level_pct",
        r.weighted_service_level_pct,
        "%",
        ">= 97%",
        t.high_is_good(r.weighted_service_level_pct, t.WEIGHTED_SERVICE_LEVEL_TARGET, t.SERVICE_LEVEL_AMBER),
        "Priority-weighted service coverage.",
    )
    add("coverage", "employees_served", m.served, "", "as high as possible", info, "Employees covered by routes.")
    add(
        "coverage",
        "employees_omitted",
        m.omitted,
        "",
        "0 preferred",
        Rating.GOOD if m.omitted == 0 else Rating.WARNING,
        "Employees left unserved.",
    )

    add(
        "efficiency",
        "avg_distance_per_served_employee_km",
        m.avg_distance_per_served_km,
        "km",
        "<= 20 km preferred",
        t.low_is_good(m.avg_distance_per_served_km, t.AVG_DISTANCE_PER_EMPLOYEE_MAX_KM, float("inf"))
        if m.served
        else info,
        "Physical distance of active routes per served employee.",
    )
    add(
        "efficiency",
        "avg_time_per_served_employee_min",
        m.avg_time_per_served_min,
        "min",
        "<= 20 min preferred",
        t.low_is_good(m.avg_time_per_served_min, t.AVG_TIME_PER_EMPLOYEE_MAX_MIN, float("inf")) if m.served else info,
        "Modelled route time per served employee.",
    )
    add(
        "efficiency",
        "productive_time_share_pct",
        m.productive_time_share_pct,
        "%",
        ">= 80% preferred",
        t.high_is_good(m.productive_time_share_pct, t.PRODUCTIVE_SHARE_MIN_PCT, 0.0),
        "Share of route time spent driving or serving (not waiting).",
    )
    add(
        "efficiency",
        "total_uncosted_distance_km",
        m.total_uncosted_distance_km,
        "km",
        "as low as possible",
        info,
        "Distance outside the objective cost logic.",
    )

    add(
        "fleet",
        "fleet_vehicles_total",
        m.routes_total,
        "",
        "scenario-defined",
        info,
        "Vehicles available in the scenario.",
    )
    add(
        "fleet", "fleet_vehicles_used", m.routes_active, "", "as needed", info, "Routes with at least one service stop."
    )
    add(
        "fleet",
        "fleet_utilization_pct",
        r.fleet_utilization_pct,
        "%",
        "60%-90% preferred",
        t.mid_band_is_good(r.fleet_utilization_pct, t.FLEET_UTILIZATION_BAND, (40.0, 100.0)),
        "Share of the fleet actively used.",
    )
    add(
        "fleet",
        "avg_demand_utilization_pct",
        m.mean_demand_utilization_pct,
        "%",
        "60%-85% preferred",
        t.mid_band_is_good(m.mean_demand_utilization_pct, t.DEMAND_UTILIZATION_BAND, (40.0, 100.0)),
        "Average demand utilization over active routes.",
    )
    add(
        "fleet",
        "p95_demand_utilization_pct",
        m.p95_demand_utilization_pct,
        "%",
        "<= 100% preferred",
        t.low_is_good(m.p95_demand_utilization_pct, t.P95_DEMAND_UTILIZATION_MAX, float("inf")),
        "95th percentile of demand utilization (most stressed routes).",
    )
    add(
        "fleet",
        "duration_balance_cv",
        m.duration_balance_cv,
        "",
        "<= 0.50 preferred",
        t.cv_rating(m.duration_balance_cv),
        "Coefficient of variation of route durations.",
    )
    add(
        "fleet",
        "service_stops_balance_cv",
        m.service_stops_balance_cv,
        "",
        "<= 0.50 preferred",
        t.cv_rating(m.service_stops_balance_cv),
        "Coefficient of variation of service stops per route.",
    )
    for name, value, unit in (
        ("workload_balance_demand_std", r.workload_balance_demand_std, ""),
        ("workload_balance_distance_std", r.workload_balance_distance_std, "km"),
        ("workload_balance_duration_std", r.workload_balance_duration_std, "min"),
    ):
        add("fleet", name, value, unit, "as low as possible", info, "Population std. dev. across active routes.")
    add(
        "fleet",
        "max_route_duration_min",
        r.max_route_duration_min,
        "min",
        "as low as possible",
        info,
        "Longest active route.",
    )
    add(
        "fleet",
        "min_route_duration_min",
        r.min_route_duration_min,
        "min",
        "as high as possible",
        info,
        "Shortest active route.",
    )
    add(
        "fleet",
        "spread_route_duration_min",
        r.spread_route_duration_min,
        "min",
        "as low as possible",
        info,
        "Longest minus shortest active route.",
    )
    add(
        "fleet",
        "max_min_duration_ratio",
        m.max_min_duration_ratio,
        "x",
        "close to 1.0 preferred",
        info,
        "Max/min route duration; high means uneven routing effort.",
    )

    add(
        "risk",
        "average_stop_wait_min",
        r.average_stop_wait_min,
        "min",
        "<= 5 min preferred",
        t.low_is_good(r.average_stop_wait_min, t.AVG_STOP_WAIT_MAX_MIN, float("inf")),
        "Average waiting time at service stops.",
    )
    add(
        "risk",
        "p95_stop_wait_min",
        r.p95_stop_wait_min,
        "min",
        "<= 15 min preferred",
        t.low_is_good(r.p95_stop_wait_min, t.P95_STOP_WAIT_MAX_MIN, float("inf")),
        "95th percentile of waiting time at service stops.",
    )

    add("sustainability", "co2_kg_per_km", r.co2_kg_per_km, "kg/km", "scenario-defined", info, "Emission factor used.")
    add(
        "sustainability",
        "estimated_co2_kg",
        r.estimated_co2_kg,
        "kg",
        "as low as possible",
        info,
        "Estimated total CO2 emissions.",
    )

    add(
        "objective",
        "objective_travel_cost",
        r.objective_travel_cost,
        "",
        "contextual",
        info,
        "Objective contribution from travel arcs.",
    )
    add(
        "objective",
        "objective_omission_penalty",
        r.objective_omission_penalty,
        "",
        "contextual",
        info,
        "Objective contribution from omitted employees.",
    )
    share = m.unattributed_cost_share
    add(
        "objective",
        "objective_unattributed_cost",
        r.objective_unattributed_cost,
        "",
        "close to 0 preferred",
        info if share is None else t.low_is_good(share, t.UNATTRIBUTED_GREEN_SHARE, t.UNATTRIBUTED_RED_SHARE),
        "Objective remainder not explained by travel and omission terms.",
    )
    add("objective", "total_objective_value", r.total_objective_value, "", "-", info, "Final objective value.")
    add("objective", "solver_branches", r.solver_branches, "", "contextual", info, "Branching decisions explored.")
    add("objective", "solver_failures", r.solver_failures, "", "contextual", info, "Failed nodes / backtracks.")
    return rows
