import copy
from pathlib import Path

import pytest

from tests.factories import make_response_dict
from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.data.process_repository import ProcessRepository
from vehicle_routing_web.data.storage import FileStorage
from vehicle_routing_web.infrastructure.settings import get_settings
from vehicle_routing_web.presentation import container

SOLVE_RESPONSE = make_response_dict()

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
        container.get_solution_service,
        container.get_batch_runner,
    ):
        cached.cache_clear()
    yield storage_dir
    runner_cache = container.get_batch_runner
    runner_cache.cache_clear()
    for cached in (
        get_settings,
        container.get_storage,
        container.get_repository,
        container.get_upload_service,
        container.get_solution_service,
    ):
        cached.cache_clear()
