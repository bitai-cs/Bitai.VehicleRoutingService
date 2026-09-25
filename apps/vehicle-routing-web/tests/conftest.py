import copy
from pathlib import Path

import pytest

from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.data.process_repository import ProcessRepository
from vehicle_routing_web.data.storage import FileStorage
from vehicle_routing_web.infrastructure.settings import get_settings
from vehicle_routing_web.presentation import container

_STOP = {
    "stop_sequence": 0,
    "stop_type": "START",
    "node_id": 0,
    "node_label": "Depot",
    "arrival_minutes": 480,
    "arrival_time": "08:00",
    "departure_minutes": 480,
    "departure_time": "08:00",
    "service_minutes": 0,
    "wait_minutes": 0,
    "cumulative_wait_minutes": 0,
    "leg_distance_km_from_prev": 0.0,
    "leg_travel_minutes_from_prev": 0,
    "cumulative_distance_km": 0.0,
    "load_before": 0,
    "load_delta": 0,
    "load_after": 0,
}

_ROUTE = {
    "vehicle_id": 0,
    "start_node_label": "Depot",
    "end_node_label": "Depot",
    "covered_demand": 2,
    "maximum_demand_coverage": 10,
    "demand_utilization_pct": 20.0,
    "departure_time": "08:00",
    "arrival_time": "09:00",
    "remaining_time_to_limit_min": 420,
    "modeled_route_duration": 60,
    "modeled_route_distance": 3.0,
    "physical_route_distance": 3.0,
    "total_service_stops": 2,
    "is_empty_route": False,
    "total_drive_time_min": 50,
    "total_wait_time_min": 0,
    "total_service_time_min": 10,
    "stops": [_STOP],
    "some_future_field": "tolerated",
}

SOLVE_RESPONSE = {
    "status": "OPTIMAL",
    "omitted_service_points": [],
    "solved_routes": [_ROUTE],
    "total_covered_service_points": 2,
    "total_modeled_route_distance": 3.0,
    "total_physical_route_distance": 3.0,
    "total_objective_value": 3000,
    "search_wall_time_ms": 12,
    "total_service_points": 2,
    "service_level_pct": 100.0,
}

PAYLOAD = b'{"nodes": {}, "vehicle_capacities": [10]}'


@pytest.fixture
def solve_response() -> dict:
    return copy.deepcopy(SOLVE_RESPONSE)


@pytest.fixture
def storage(tmp_path: Path) -> FileStorage:
    return FileStorage(tmp_path / "storage")


@pytest.fixture
def repository(storage: FileStorage) -> ProcessRepository:
    return ProcessRepository(storage)


@pytest.fixture
def add_process(storage: FileStorage):
    """Register a process through the real upload path; returns its id."""
    service = UploadService(storage, max_upload_bytes=10_000)
    counter = iter(range(1000))

    def _add(process_id: str) -> str:
        payload = b'{"n": %d}' % next(counter)
        service.upload(process_id, payload)
        return process_id

    return _add


@pytest.fixture
def isolated_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the composition root at a temp storage dir and reset cached singletons."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("VRW_STORAGE_DIR", str(storage_dir))
    for cached in (
        get_settings,
        container.get_storage,
        container.get_repository,
        container.get_upload_service,
        container.get_batch_runner,
    ):
        cached.cache_clear()
    yield storage_dir
    runner_cache = container.get_batch_runner
    runner_cache.cache_clear()
    for cached in (get_settings, container.get_storage, container.get_repository, container.get_upload_service):
        cached.cache_clear()
