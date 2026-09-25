"""Solution service and dashboard composition/callback behaviour (no browser)."""

import json
import os

import pytest
from dash import no_update

from tests.factories import make_payload_dict, make_response_dict, make_solution
from vehicle_routing_web.application.solution_service import SolutionService
from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.domain.artifacts import RESULT_FILENAME, ProcessStatus
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, StorageCorruptedError
from vehicle_routing_web.presentation.dashboard import callbacks, header, tabs


def _solved(storage, repository, process_id="alpha", payload=None):
    body = {**(payload or make_payload_dict()), "tag": process_id}  # unique content; extra keys are ignored
    UploadService(storage, 10_000_000).upload(process_id, json.dumps(body).encode())
    repository.begin_processing(process_id)
    repository.complete_success(process_id, make_response_dict())


class TestSolutionService:
    def test_loads_solution_with_metrics_and_timestamp(self, storage, repository):
        _solved(storage, repository)
        loaded = SolutionService(repository).load("alpha")

        assert loaded.status is ProcessStatus.SOLVED
        assert loaded.solution.metrics.routes_active == 2
        assert loaded.solution.scenario.label(3) == "E3"
        assert loaded.solution.generated_at.tzinfo is not None

    def test_second_load_is_served_from_cache(self, storage, repository):
        _solved(storage, repository)
        service = SolutionService(repository)

        assert service.load("alpha").solution is service.load("alpha").solution

    def test_rerun_invalidates_cache(self, storage, repository):
        _solved(storage, repository)
        service = SolutionService(repository)
        first = service.load("alpha").solution
        changed = make_response_dict()
        changed["status"] = "OPTIMAL"
        repository.begin_processing("alpha")
        repository.complete_success("alpha", changed)
        path = storage.process_dir("alpha") / RESULT_FILENAME
        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 5_000_000_000))

        second = service.load("alpha").solution

        assert second is not first
        assert second.response.status == "OPTIMAL"

    def test_cache_is_bounded(self, storage, repository):
        service = SolutionService(repository, cache_size=2)
        for name in ("a1", "b2", "c3"):
            _solved(storage, repository, name)
            service.load(name)

        assert len(service._cache) == 2

    def test_non_solved_states_carry_no_solution(self, storage, repository, add_process):
        add_process("fresh")
        assert SolutionService(repository).load("fresh") == SolutionService(repository).load("fresh")
        assert SolutionService(repository).load("fresh").status is ProcessStatus.PENDING
        repository.begin_processing("fresh")
        assert SolutionService(repository).load("fresh").solution is None
        repository.complete_failure("fresh", error_type="timeout", message="slow")
        failed = SolutionService(repository).load("fresh")
        assert failed.status is ProcessStatus.FAILED
        assert failed.error["message"] == "slow"

    def test_payload_that_is_not_a_scenario_is_a_storage_error(self, storage, repository):
        UploadService(storage, 10_000).upload("bad1", b'{"nodes": {}}')
        repository.begin_processing("bad1")
        repository.complete_success("bad1", make_response_dict())

        with pytest.raises(StorageCorruptedError):
            SolutionService(repository).load("bad1")

    def test_unknown_and_invalid_ids(self, repository):
        service = SolutionService(repository)
        with pytest.raises(ProcessNotFoundError):
            service.load("ghost")
        with pytest.raises(InvalidProcessIdError):
            service.load("../x")


class TestComposition:
    @pytest.mark.parametrize("tab_id", [tab_id for tab_id, _ in tabs.TAB_LABELS])
    def test_every_tab_builds_for_all_and_selected_vehicle(self, tab_id):
        solution = make_solution()
        for vehicle in (None, 0, 1):
            assert tabs.build_tab(tab_id, solution, vehicle) is not None

    def test_every_tab_builds_without_omitted_or_active_routes(self):
        data = make_response_dict()
        data.update(omitted_service_points=[], solved_routes=[data["solved_routes"][2]], total_covered_service_points=0)
        solution = make_solution(response=data)
        for tab_id, _ in tabs.TAB_LABELS:
            assert tabs.build_tab(tab_id, solution, None) is not None

    def test_unknown_tab_is_reported(self):
        assert "Unknown tab" in str(tabs.build_tab("nope", make_solution(), None))

    def test_tab_order_follows_the_specification(self):
        assert [label for _, label in tabs.TAB_LABELS] == [
            "Geography", "Coverage", "Efficiency", "Load balance", "Stops", "Objective", "Sustainability", "Summary",
        ]  # fmt: skip

    def test_vehicle_options_list_only_active_routes(self):
        options = tabs.vehicle_options(make_solution(), all_label="All routes")
        assert [o["value"] for o in options] == ["all", "0", "1"]

    @pytest.mark.parametrize(("raw", "expected"), [(None, None), ("all", None), ("", None), ("1", 1), ("x", None)])
    def test_parse_vehicle(self, raw, expected):
        assert tabs.parse_vehicle(raw) == expected

    def test_executive_summary_shows_all_spec_kpis_with_text_status(self):
        text = str(header.build_executive_summary(make_solution()))
        for label in (
            "Status",
            "Search time",
            "Service level",
            "Omitted employees",
            "Total distance",
            "Total duration",
            "Objective value",
            "Fleet utilization",
        ):
            assert label in text
        assert "83.3 %" in text
        assert "Red: service level below 85%" in text  # semaphore is spelled out, not colour-only
        assert "1,234 ms" in text

    def test_header_shows_infeasibility_hints(self):
        data = make_response_dict()
        data["infeasibility_hints"] = ["Vehicle capacity too small"]
        assert "Vehicle capacity too small" in str(header.build_header(make_solution(response=data)))

    def test_solver_status_ratings(self):
        assert header.status_rating("OPTIMAL").value == "good"
        assert header.status_rating("TIMEOUT").value == "warning"
        assert header.status_rating("INFEASIBLE").value == "bad"

    def test_sustainability_tab_states_unavailable_widgets(self):
        text = str(tabs.build_tab(tabs.TAB_SUSTAINABILITY, make_solution(), None))
        for expected in ("7.000 kg", "0.200000 kg/km", "1.400 kg"):
            assert expected in text
        assert "64.29 %" in text  # deadhead ratio 22.5 / 35


class TestCallbacks:
    @pytest.fixture
    def solved_app(self, isolated_container):
        from vehicle_routing_web.presentation.container import get_repository, get_storage

        _solved(get_storage(), get_repository())
        return {"process_id": "alpha"}

    def test_render_tab_returns_tab_content(self, solved_app):
        content = callbacks.render_tab(tabs.TAB_COVERAGE, solved_app, {"vehicle": None})
        assert "Omitted employees" in str(content)

    def test_render_tab_uses_shared_vehicle_selection(self, solved_app):
        content = str(callbacks.render_tab(tabs.TAB_STOPS, solved_app, {"vehicle": 1}))
        assert "value='1'" in content

    def test_render_tab_ignores_unknown_vehicle(self, solved_app):
        assert "value='all'" in str(callbacks.render_tab(tabs.TAB_STOPS, solved_app, {"vehicle": 999}))

    @pytest.mark.parametrize("context", [None, {}, {"process_id": 5}, {"process_id": "../x"}, {"process_id": "ghost"}])
    def test_bad_context_gives_alert_not_exception(self, isolated_container, context):
        assert "Alert" in str(callbacks.render_tab(tabs.TAB_GEOGRAPHY, context, None))

    def test_geography_selection_updates_map_detail_and_store(self, solved_app):
        figure, detail, disabled, selection = callbacks.select_geography_vehicle("1", solved_app)

        assert disabled is False
        assert selection == {"vehicle": 1}
        assert "Vehicle ID" in str(detail)
        assert {tr.name: tr.opacity for tr in figure.data if tr.name in ("Vehicle 0", "Vehicle 1")}["Vehicle 0"] < 1

    def test_geography_all_routes_disables_stops_button(self, solved_app):
        _, detail, disabled, selection = callbacks.select_geography_vehicle("all", solved_app)
        assert (disabled, selection) == (True, {"vehicle": None})
        assert "Select a vehicle" in str(detail)

    def test_forged_vehicle_value_is_treated_as_all(self, solved_app):
        assert callbacks.select_geography_vehicle("12345", solved_app)[3] == {"vehicle": None}

    def test_stops_selection_updates_gantt_and_table(self, solved_app):
        gantt, table, selection = callbacks.select_stops_vehicle("0", solved_app)
        assert selection == {"vehicle": 0}
        assert "Graph" in str(gantt)
        assert "AgGrid" in str(table)

    def test_stops_all_vehicles_has_no_gantt(self, solved_app):
        gantt, _, _ = callbacks.select_stops_vehicle("all", solved_app)
        assert "Select a single vehicle" in str(gantt)

    def test_open_stops_only_reacts_to_real_clicks(self):
        assert callbacks.open_stops_tab(None) is no_update
        assert callbacks.open_stops_tab(0) is no_update
        assert callbacks.open_stops_tab(1) == tabs.TAB_STOPS

    def test_map_click_selects_the_omitted_row(self):
        click = {"points": [{"customdata": [8, "E8", "high"]}]}
        assert callbacks.highlight_omitted_row(click) == [{"row_key": "8"}]

    @pytest.mark.parametrize("click", [None, {}, {"points": []}, {"points": [{"customdata": ["x"]}]}, {"points": [{}]}])
    def test_map_click_without_usable_point_changes_nothing(self, click):
        assert callbacks.highlight_omitted_row(click) is no_update

    def test_csv_export_triggers_only_on_click(self):
        assert callbacks.export_grid_csv(None) is no_update
        assert callbacks.export_grid_csv(2) is True

    def test_failed_solution_page_shows_stored_error(self, isolated_container):
        from vehicle_routing_web.presentation.app import create_app
        from vehicle_routing_web.presentation.container import get_repository, get_upload_service

        create_app()
        from vehicle_routing_web.presentation.pages import dashboard

        get_upload_service().upload("run9", json.dumps(make_payload_dict()).encode())
        get_repository().begin_processing("run9")
        get_repository().complete_failure("run9", error_type="timeout", message="Too slow")

        assert "Too slow" in str(dashboard.layout(process_id="run9"))


def test_grid_rows_get_string_row_keys():
    from vehicle_routing_web.presentation.dashboard.components import with_row_keys
    from vehicle_routing_web.visualization import tables

    rows = with_row_keys(tables.routes_table(make_solution()))

    assert [r["row_key"] for r in rows] == ["0", "1", "2"]
    assert all(isinstance(r["row_key"], str) for r in rows)
