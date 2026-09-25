import math

import pytest

from tests.factories import make_response_dict, make_solution
from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.domain.kpi_table import SECTION_TITLES, build_kpi_rows
from vehicle_routing_web.domain.metrics import compute_metrics
from vehicle_routing_web.domain.scenario import Scenario
from vehicle_routing_web.domain.solve_response import SolveResponse
from vehicle_routing_web.domain.stats import coefficient_of_variation, mean, percentile, population_std


class TestStats:
    def test_percentile_interpolates_linearly(self):
        assert percentile([10, 20, 30, 40], 0.95) == pytest.approx(38.5)
        assert percentile([40, 60], 0.95) == pytest.approx(59.0)
        assert percentile([1, 2, 3], 0.5) == 2
        assert percentile([1, 2, 3], 0.0) == 1
        assert percentile([1, 2, 3], 1.0) == 3

    def test_percentile_edge_cases(self):
        assert percentile([], 0.95) == 0.0
        assert percentile([7], 0.95) == 7.0

    def test_population_std_divides_by_n(self):
        assert population_std([60, 40]) == pytest.approx(10.0)
        assert population_std([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.0)
        assert population_std([]) == 0.0

    def test_cv(self):
        assert coefficient_of_variation([60, 40]) == pytest.approx(0.2)
        assert coefficient_of_variation([0, 0]) == 0.0
        assert coefficient_of_variation([]) == 0.0
        assert mean([]) == 0.0


class TestDerivedMetrics:
    """Expected numbers are worked out by hand in tests/factories.py."""

    def test_counts_use_all_routes_but_balance_uses_active_only(self):
        m = make_solution().metrics
        assert (m.routes_total, m.routes_active, m.routes_empty) == (3, 2, 1)
        assert (m.served, m.omitted, m.total_employees) == (5, 1, 6)

    def test_balance_statistics_ignore_the_empty_route(self):
        m = make_solution().metrics
        assert m.duration_balance_cv == pytest.approx(0.2)  # durations 60, 40 (the empty 0 would change this)
        assert m.service_stops_balance_cv == pytest.approx(0.5 / 2.5)
        assert m.max_min_duration_ratio == pytest.approx(1.5)

    def test_demand_utilization(self):
        m = make_solution().metrics
        assert m.mean_demand_utilization_pct == pytest.approx(50.0)
        assert m.p95_demand_utilization_pct == pytest.approx(59.0)

    def test_efficiency(self):
        m = make_solution().metrics
        assert m.productive_time_share_pct == pytest.approx(95.0)  # (55 + 40) / (60 + 40)
        assert m.avg_distance_per_served_km == pytest.approx(7.0)  # 35 km / 5 served
        assert m.avg_time_per_served_min == pytest.approx(20.0)
        assert m.total_uncosted_distance_km == pytest.approx(5.0)
        assert m.total_modeled_duration_min == pytest.approx(100.0)

    def test_sustainability_and_objective_ratios(self):
        m = make_solution().metrics
        assert m.deadhead_ratio_pct == pytest.approx(22.5 / 35 * 100)
        assert m.co2_per_served_employee_kg == pytest.approx(7.0 / 5)
        assert m.unattributed_cost_share == pytest.approx(0.005)

    def test_undefined_ratios_are_none_not_zero(self):
        data = make_response_dict()
        data.update(
            solved_routes=[data["solved_routes"][2]],  # only the empty route
            total_covered_service_points=0,
            total_physical_route_distance=0.0,
            total_objective_value=0,
        )
        m = compute_metrics(SolveResponse.model_validate(data))
        assert m.max_min_duration_ratio is None
        assert m.deadhead_ratio_pct is None
        assert m.co2_per_served_employee_kg is None
        assert m.unattributed_cost_share is None
        assert m.duration_balance_cv == 0.0
        assert m.avg_time_per_served_min == 0.0


class TestKpiTable:
    def test_every_section_is_present_and_metrics_unique(self):
        rows = build_kpi_rows(make_solution())
        assert {r.section for r in rows} == set(SECTION_TITLES)
        names = [r.metric for r in rows]
        assert len(names) == len(set(names))

    def test_ratings_follow_targets(self):
        by_name = {r.metric: r for r in build_kpi_rows(make_solution())}
        assert by_name["service_level_pct"].rating is t.Rating.BAD  # 83.3% < 85%
        assert by_name["employees_omitted"].rating is t.Rating.WARNING
        assert by_name["duration_balance_cv"].rating is t.Rating.GOOD
        assert by_name["objective_unattributed_cost"].rating is t.Rating.GOOD
        assert by_name["max_min_duration_ratio"].rating is t.Rating.INFO

    def test_unavailable_value_is_none(self):
        data = make_response_dict()
        data["solved_routes"] = [data["solved_routes"][2]]
        row = next(r for r in build_kpi_rows(make_solution(response=data)) if r.metric == "max_min_duration_ratio")
        assert row.value is None


class TestThresholds:
    @pytest.mark.parametrize(
        ("pct", "rating"), [(100, "good"), (95, "good"), (94.9, "warning"), (85, "warning"), (84.9, "bad")]
    )
    def test_service_level_semaphore(self, pct, rating):
        assert t.service_level_rating(pct).value == rating

    @pytest.mark.parametrize(
        ("cv", "rating"), [(0.0, "good"), (0.3, "good"), (0.31, "warning"), (0.5, "warning"), (0.51, "bad")]
    )
    def test_cv_rating(self, cv, rating):
        assert t.cv_rating(cv).value == rating

    def test_mid_band(self):
        assert t.mid_band_is_good(75, (60, 90), (40, 100)) is t.Rating.GOOD
        assert t.mid_band_is_good(95, (60, 90), (40, 100)) is t.Rating.WARNING
        assert t.mid_band_is_good(20, (60, 90), (40, 100)) is t.Rating.BAD


class TestScenario:
    def test_parses_payload_ignoring_cost_matrix(self):
        from tests.factories import make_payload_dict

        scenario = Scenario.model_validate(make_payload_dict())
        assert scenario.coord(3) == (2.0, 1.0)
        assert scenario.priority(5) == "high"
        assert scenario.priority(0) is None
        assert scenario.employee_node_ids == [3, 4, 5, 6, 7, 8]
        assert scenario.leg_counted(1, first=True) == (False, True)
        assert scenario.leg_counted(2, first=False) == (False, False)
        assert scenario.leg_counted(99, first=True) == (True, True)
        assert not hasattr(scenario, "cost_matrix")

    def test_rejects_references_to_unknown_nodes(self):
        from tests.factories import make_payload_dict

        payload = make_payload_dict()
        payload["vehicle_end_nodes"] = [1, 2, 99]
        with pytest.raises(ValueError, match="not defined"):
            Scenario.model_validate(payload)

    def test_rejects_unknown_priority(self):
        from tests.factories import make_payload_dict

        payload = make_payload_dict()
        payload["service_point_priorities"]["3"] = "urgent"
        with pytest.raises(ValueError, match="priorit"):
            Scenario.model_validate(payload)


def test_omitted_employees_come_from_payload_priorities():
    solution = make_solution()
    (omitted,) = solution.omitted_employees
    assert (omitted.node_id, omitted.label, omitted.priority, omitted.x, omitted.y) == (8, "E8", "high", -5.0, -5.0)


def test_omitted_node_without_priority_is_not_invented():
    data = make_response_dict()
    data["omitted_service_points"] = [8, 2]  # node 2 is a depot, not an employee
    assert [e.node_id for e in make_solution(response=data).omitted_employees] == [8]


def test_math_is_finite_for_factory_solution():
    m = make_solution().metrics
    assert all(math.isfinite(v) for v in (m.duration_balance_cv, m.mean_demand_utilization_pct))
