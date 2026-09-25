"""Semantic checks of figure/table builders (no snapshots, no Dash)."""

from itertools import pairwise

import pytest

from tests.factories import make_payload_dict, make_response_dict, make_solution
from vehicle_routing_web.domain import thresholds as t
from vehicle_routing_web.visualization import balance, coverage, efficiency, gauges, geography, objective, stops, tables


def _names(fig):
    return [trace.name for trace in fig.data]


def _no_omitted():
    data = make_response_dict()
    data.update(omitted_service_points=[], omitted_high_priority_count=0, total_covered_service_points=6)
    return make_solution(response=data)


class TestGeographyMap:
    def test_has_equal_aspect_and_axis_titles(self):
        fig = geography.build_route_map(make_solution())
        assert fig.layout.yaxis.scaleanchor == "x"
        assert fig.layout.yaxis.scaleratio == 1
        assert fig.layout.xaxis.title.text == "x (km)"

    def test_one_marker_trace_per_active_route_and_none_for_empty(self):
        fig = geography.build_route_map(make_solution())
        assert "Vehicle 0" in _names(fig)
        assert "Vehicle 1" in _names(fig)
        assert "Vehicle 2" not in _names(fig)

    def test_omitted_employees_are_red_x_markers(self):
        fig = geography.build_route_map(make_solution())
        omitted = next(tr for tr in fig.data if tr.name == "Omitted employees")
        assert omitted.marker.symbol == "x"
        assert list(omitted.x) == [-5.0]
        assert omitted.customdata[0][0] == 8

    def test_no_omitted_trace_when_all_served(self):
        assert "Omitted employees" not in _names(geography.build_route_map(_no_omitted()))

    def test_selection_dims_other_routes(self):
        fig = geography.build_route_map(make_solution(), selected_vehicle=1)
        markers = {tr.name: tr.opacity for tr in fig.data if tr.name in ("Vehicle 0", "Vehicle 1")}
        assert markers == {"Vehicle 0": geography.DIMMED_OPACITY, "Vehicle 1": 1.0}

    def test_no_selection_shows_all_routes_fully(self):
        fig = geography.build_route_map(make_solution())
        assert {tr.opacity for tr in fig.data if tr.name in ("Vehicle 0", "Vehicle 1")} == {1.0}

    def test_first_and_last_leg_line_style_follow_payload_flags(self):
        def dashes(solution, vehicle_color):
            fig = geography.build_route_map(solution)
            return [tr.line.dash for tr in fig.data if tr.mode == "lines" and tr.line.color == vehicle_color]

        v0, v1 = "#0072B2", "#D55E00"  # route colours of vehicles 0 and 1
        base = make_solution()
        assert dashes(base, v0) == ["solid", "solid", "solid"]  # all legs counted
        assert dashes(base, v1)[0] == "dash"  # first leg: cost not counted
        assert dashes(base, v1)[-1] == "solid"

        payload = make_payload_dict()
        payload["include_last_leg_cost"] = [True, False, False]
        payload["include_last_leg_time"] = [True, False, False]
        assert dashes(make_solution(payload=payload), v1)[-1] == "dot"  # neither counted

    def test_stop_order_numbers_are_annotated(self):
        fig = geography.build_route_map(make_solution())
        v0 = next(tr for tr in fig.data if tr.name == "Vehicle 0")
        assert list(v0.text) == ["0", "1", "2", "3", "4"]

    def test_vehicle_detail_rows(self):
        rows = dict(geography.vehicle_detail_rows(make_solution().routes_by_vehicle[0]))
        assert rows["Vehicle ID"] == "0"
        assert rows["Employees served"] == "3"
        assert rows["Total duration"] == "60 min"
        assert rows["Physical distance"] == "20.000 km"
        assert rows["Capacity utilization"] == "60.0 %"
        assert rows["Departure time"] == "07:30"
        assert rows["Time remaining to limit"] == "30 min"


class TestCoverage:
    def test_donut_values_and_center_label(self):
        fig = coverage.build_coverage_donut(make_solution())
        assert list(fig.data[0].values) == [5, 1]
        assert "83.3%" in fig.layout.annotations[0].text

    def test_omitted_by_priority_counts(self):
        fig = coverage.build_omitted_by_priority(make_solution())
        assert list(fig.data[0].y) == [0, 0, 1]
        assert list(fig.data[0].x) == ["Low priority", "Medium priority", "High priority"]

    def test_empty_states_explain_themselves(self):
        solution = _no_omitted()
        for fig in (coverage.build_omitted_by_priority(solution), coverage.build_omitted_map(solution)):
            assert len(fig.data) == 0
            assert "No omitted" in fig.layout.annotations[0].text

    def test_omitted_map_groups_by_priority(self):
        fig = coverage.build_omitted_map(make_solution())
        assert _names(fig) == ["High priority"]
        assert fig.data[0].customdata[0][0] == 8


class TestGauges:
    def test_bands_and_target(self):
        fig = gauges.build_gauge(96.0, "Service", gauges.SERVICE_LEVEL_BANDS, target=95, suffix="%")
        gauge = fig.data[0].gauge
        assert [(s.range[0], s.range[1]) for s in gauge.steps] == [(0, 60), (60, 85), (85, 95), (95, 100)]
        assert gauge.threshold.value == 95
        assert fig.data[0].value == 96.0

    def test_band_label_is_textual(self):
        assert gauges.band_label(96, gauges.SERVICE_LEVEL_BANDS).startswith("Excellent")
        assert gauges.band_label(50, gauges.SERVICE_LEVEL_BANDS).startswith("Critical")
        assert gauges.band_label(100, gauges.SERVICE_LEVEL_BANDS).startswith("Excellent")
        assert gauges.band_label(95, gauges.FLEET_UTILIZATION_BANDS).startswith("Highly")

    def test_badge_rating_comes_from_the_same_band_as_the_label(self):
        bands = gauges.SERVICE_LEVEL_BANDS
        assert gauges.band_rating(83.3, bands) is t.Rating.WARNING
        assert gauges.band_label(83.3, bands).startswith("Warning")
        assert gauges.band_rating(40, bands) is t.Rating.BAD
        assert gauges.band_rating(99, bands) is t.Rating.GOOD
        assert gauges.band_rating(95, gauges.FLEET_UTILIZATION_BANDS) is t.Rating.INFO

    @pytest.mark.parametrize(("value", "expected"), [(0.2, 1.0), (1.0, 1.5), (1.4, 2.0), (3.0, 3.5)])
    def test_cv_axis_grows_to_keep_value_on_scale(self, value, expected):
        assert gauges.cv_axis_max(value) == expected
        assert gauges.cv_axis_max(value) >= value


class TestEfficiency:
    def test_distributions_use_active_routes_only(self):
        fig = efficiency.build_duration_distribution(make_solution())
        assert sorted(fig.data[0].y) == [40, 60]
        assert list(fig.data[0].customdata) in ([0, 1], [1, 0])
        assert "1.50x" in fig.layout.annotations[-1].text

    def test_reference_lines_are_min_and_max(self):
        fig = efficiency.build_duration_distribution(make_solution())
        assert sorted(s.y0 for s in fig.layout.shapes) == [40, 60]

    def test_time_composition_is_100_percent_stack_with_slack(self):
        fig = efficiency.build_time_composition(make_solution())
        assert fig.layout.barnorm == "percent"
        assert [tr.name for tr in fig.data] == ["Drive", "Service", "Wait", "Slack / idle"]
        assert list(fig.data[0].x) == ["V0", "V1"]
        assert list(fig.data[0].y) == [40, 30]
        assert list(fig.data[3].y) == [0, 0]  # 60-40-15-5, 40-30-10-0

    def test_slack_never_negative(self):
        assert efficiency.slack_minutes(10, 8, 5, 0) == 0
        assert efficiency.slack_minutes(30, 10, 5, 5) == 10

    def test_utilization_scatter_marks_p95(self):
        fig = efficiency.build_utilization_vs_duration(make_solution())
        assert list(fig.data[0].x) == [60.0, 40.0]
        assert fig.layout.shapes[0].x0 == pytest.approx(59.0)

    def test_empty_when_no_active_routes(self):
        data = make_response_dict()
        data["solved_routes"] = [data["solved_routes"][2]]
        solution = make_solution(response=data)
        assert len(efficiency.build_duration_distribution(solution).data) == 0
        assert len(efficiency.build_time_composition(solution).data) == 0


class TestBalance:
    def test_normalize_column(self):
        assert balance.normalize_column([10, 20, 30]) == [0.0, 0.5, 1.0]
        assert balance.normalize_column([5, 5]) == [0.0, 0.0]
        assert balance.normalize_column([]) == []

    def test_rank_column(self):
        assert balance.rank_column([10, 20, 30, 20]) == [25.0, 75.0, 100.0, 75.0]

    def test_route_matrix_shape_and_range(self):
        matrix = balance.build_route_matrix(make_solution())
        assert matrix.vehicle_ids == [0, 1]
        assert len(matrix.column_labels) == 6
        assert matrix.absolute[0][0] == 60.0  # duration of vehicle 0
        assert all(0.0 <= v <= 1.0 for row in matrix.normalized for v in row)
        assert matrix.normalized[0][0] == 1.0
        assert matrix.normalized[1][0] == 0.0

    def test_heatmap_uses_normalized_values(self):
        fig = balance.build_route_heatmap(make_solution())
        assert fig.data[0].zmin == 0
        assert fig.data[0].zmax == 1
        assert list(fig.data[0].y) == ["Vehicle 0", "Vehicle 1"]

    def test_std_bars_map_to_response_fields(self):
        fig = balance.build_std_bars(make_solution())
        assert list(fig.data[0].y) == [0.5, 2.5, 10.0]

    def test_summary_stats(self):
        stats = {label: value for label, value, _ in balance.balance_stats(make_solution())}
        assert stats["Max route duration"] == "60 min"
        assert stats["Duration spread"] == "20 min"
        assert stats["Max/min duration ratio"] == "1.500000"
        assert stats["Average demand utilization"] == "50.00 %"


class TestStopsGantt:
    def test_segments_are_positioned_from_reported_fields(self):
        route = make_solution().routes_by_vehicle[0]
        segs = {(s.stop_sequence, s.activity): (s.start_min, s.duration_min) for s in stops.route_segments(route)}
        assert segs[(1, "Drive")] == (0, 10)
        assert segs[(1, "Service")] == (10, 5)
        assert segs[(2, "Drive")] == (15, 10)
        assert segs[(2, "Wait")] == (25, 5)
        assert segs[(2, "Service")] == (30, 5)
        assert segs[(4, "Drive")] == (50, 10)  # END stop: drive only

    def test_segments_never_overlap_and_end_at_route_duration(self):
        route = make_solution().routes_by_vehicle[0]
        segs = sorted(stops.route_segments(route), key=lambda s: s.start_min)
        for a, b in pairwise(segs):
            assert a.start_min + a.duration_min <= b.start_min
        assert segs[-1].start_min + segs[-1].duration_min == route.modeled_route_duration

    def test_gantt_traces_by_activity(self):
        fig = stops.build_gantt(make_solution().routes_by_vehicle[0])
        assert sorted(tr.name for tr in fig.data) == ["Drive", "Service", "Wait"]
        assert fig.layout.xaxis.title.text == "Minutes from route start"

    def test_empty_route_has_message(self):
        fig = stops.build_gantt(make_solution().routes_by_vehicle[2])
        assert len(fig.data) == 0


class TestObjective:
    def test_donut_parts(self):
        fig = objective.build_objective_donut(make_solution())
        assert list(fig.data[0].values) == [695, 300, 5]
        assert "1,000" in fig.layout.annotations[0].text

    def test_zero_objective_is_explained(self):
        data = make_response_dict()
        data.update(
            total_objective_value=0,
            objective_travel_cost=0,
            objective_omission_penalty=0,
            objective_unattributed_cost=0,
        )
        assert len(objective.build_objective_donut(make_solution(response=data)).data) == 0

    def test_alerts_green_and_info_for_well_explained_objective(self):
        levels = {a.level for a in objective.objective_alerts(make_solution())}
        assert levels == {t.Rating.INFO, t.Rating.GOOD}

    def test_alert_red_when_unattributed_over_ten_percent(self):
        data = make_response_dict()
        data.update(objective_unattributed_cost=200)
        alerts = objective.objective_alerts(make_solution(response=data))
        assert alerts[0].level is t.Rating.BAD
        assert t.Rating.GOOD not in {a.level for a in alerts}

    def test_alert_amber_for_many_solver_failures(self):
        data = make_response_dict()
        data.update(solver_failures=10_001)
        assert any(a.level is t.Rating.WARNING for a in objective.objective_alerts(make_solution(response=data)))

    def test_info_alert_reports_search_time(self):
        info = next(a for a in objective.objective_alerts(make_solution()) if a.level is t.Rating.INFO)
        assert "1,234 ms" in info.message


class TestTables:
    def test_omitted_table(self):
        spec = tables.omitted_table(make_solution())
        assert spec.row_id == "node_id"
        assert spec.row_data == [
            {"node_id": 8, "employee": "E8", "priority": "high", "priority_rank": 3, "x_km": -5.0, "y_km": -5.0}
        ]
        assert "reference_distance_km" not in {c["field"] for c in spec.column_defs}

    def test_routes_table_includes_empty_routes_with_flag(self):
        spec = tables.routes_table(make_solution())
        rows = {r["vehicle_id"]: r for r in spec.row_data}
        assert rows[2]["empty_route"] == "Yes"
        assert rows[2]["util_band"] == "none"
        assert rows[0]["empty_route"] == "No"
        assert rows[0]["util_band"] == "mid"  # 60%
        assert rows[1]["util_band"] == "low"  # 40%
        assert [r["vehicle_id"] for r in spec.row_data] == [0, 1, 2]

    def test_stops_table_for_one_vehicle(self):
        spec = tables.stops_table(make_solution(), 0)
        assert spec.row_id == "stop_key"
        assert [r["stop_type"] for r in spec.row_data] == ["START", "SERVICE", "SERVICE", "SERVICE", "END"]
        assert [r["wait_band"] for r in spec.row_data] == ["edge", "none", "some", "none", "edge"]
        assert spec.row_data[3]["load_after"] == 3
        assert spec.row_data[2]["cumulative_wait_minutes"] == 5

    def test_stops_table_aggregated_covers_active_routes_only(self):
        spec = tables.stops_table(make_solution(), None)
        assert {r["vehicle_id"] for r in spec.row_data} == {0, 1}
        keys = [r["stop_key"] for r in spec.row_data]
        assert len(keys) == len(set(keys))

    def test_unknown_vehicle_falls_back_to_aggregate(self):
        assert len(tables.stops_table(make_solution(), 99).row_data) == len(
            tables.stops_table(make_solution(), None).row_data
        )

    def test_stops_table_is_bounded(self, monkeypatch):
        monkeypatch.setattr(tables, "MAX_STOP_ROWS", 3)
        spec = tables.stops_table(make_solution(), 0)
        assert len(spec.row_data) == 3
        assert spec.truncated

    def test_row_ids_reference_existing_unique_fields(self):
        solution = make_solution()
        specs = [tables.omitted_table(solution), tables.routes_table(solution), tables.stops_table(solution, None)]
        specs += list(tables.kpi_tables(solution).values())
        for spec in specs:
            ids = [str(r[spec.row_id]) for r in spec.row_data]
            assert len(ids) == len(set(ids))
            assert spec.row_id in {c["field"] for c in spec.column_defs} or spec.row_id in (
                spec.row_data[0] if spec.row_data else {}
            )

    def test_numeric_columns_stay_numeric(self):
        spec = tables.routes_table(make_solution())
        assert all(isinstance(r["physical_distance_km"], float) for r in spec.row_data)
        assert all(isinstance(r["modeled_duration_min"], int) for r in spec.row_data)

    def test_kpi_tables_have_text_status_for_every_row(self):
        for spec in tables.kpi_tables(make_solution()).values():
            assert spec.row_data
            assert all(r["status"] in {"Good", "Warning", "Poor", "Info", "Not available"} for r in spec.row_data)

    def test_kpi_unavailable_value_is_labelled(self):
        data = make_response_dict()
        data["solved_routes"] = [data["solved_routes"][2]]
        fleet = tables.kpi_tables(make_solution(response=data))["fleet"]
        row = next(r for r in fleet.row_data if r["metric"] == "max_min_duration_ratio")
        assert row["value"] is None
        assert row["status"] == "Not available"
