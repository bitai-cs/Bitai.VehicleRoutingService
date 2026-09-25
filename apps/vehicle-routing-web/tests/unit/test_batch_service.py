import json
import threading
from concurrent.futures import wait

import pytest

from vehicle_routing_web.application.batch_service import BatchRunner
from vehicle_routing_web.domain.artifacts import ERROR_FILENAME, PENDING_FILENAME, ProcessStatus
from vehicle_routing_web.domain.exceptions import SolveApiError


class FakeClient:
    def __init__(self, response, error=None):
        self.response = response
        self.error = error
        self.calls: list[bytes] = []

    def solve(self, payload_json):
        self.calls.append(payload_json)
        if self.error:
            raise self.error
        return self.response


class GatedClient:
    """Blocks every call until released; records peak concurrency."""

    def __init__(self, response):
        self.response = response
        self.release = threading.Event()
        self.entered = threading.Semaphore(0)
        self._lock = threading.Lock()
        self.current = 0
        self.peak = 0

    def solve(self, _payload):
        with self._lock:
            self.current += 1
            self.peak = max(self.peak, self.current)
        self.entered.release()
        assert self.release.wait(timeout=10)
        with self._lock:
            self.current -= 1
        return self.response


@pytest.fixture
def runners():
    created = []

    def make(repository, client, workers=4):
        runner = BatchRunner(repository, client, workers)
        created.append(runner)
        return runner

    yield make
    for runner in created:
        runner.shutdown()


def _run(runner, ids):
    submission, futures = runner.submit(ids)
    wait(futures, timeout=10)
    return submission


def test_successful_batch_stores_results_for_every_process(repository, add_process, solve_response, runners):
    ids = [add_process(name) for name in ("a1", "b2", "c3")]
    client = FakeClient(solve_response)

    submission = _run(runners(repository, client), ids)

    assert submission.started == tuple(ids)
    assert {i.process_id: i.status for i in repository.list_processes()} == dict.fromkeys(ids, ProcessStatus.SOLVED)
    assert len(client.calls) == 3
    assert all(call.startswith(b'{"n"') for call in client.calls)  # the stored payload bytes


def test_marker_is_visible_immediately_after_submit(repository, add_process, solve_response, runners):
    add_process("a1")
    client = GatedClient(solve_response)
    runner = runners(repository, client)

    _, futures = runner.submit(["a1"])

    assert repository.get_status("a1") is ProcessStatus.RUNNING
    assert runner.active_ids() == {"a1"}
    client.release.set()
    wait(futures, timeout=10)
    assert repository.get_status("a1") is ProcessStatus.SOLVED
    assert runner.active_ids() == frozenset()


def test_solves_run_in_parallel_up_to_the_cap(repository, add_process, solve_response, runners):
    ids = [add_process(f"p{i}") for i in range(6)]
    client = GatedClient(solve_response)
    runner = runners(repository, client, workers=3)

    _, futures = runner.submit(ids)
    for _ in range(3):
        assert client.entered.acquire(timeout=10)  # three calls are in flight together
    assert not client.entered.acquire(timeout=0.3)  # the fourth waits for a free worker
    client.release.set()
    wait(futures, timeout=10)

    assert client.peak == 3
    assert all(i.status is ProcessStatus.SOLVED for i in repository.list_processes())


def test_api_failure_writes_error_file_and_no_result(repository, storage, add_process, runners):
    add_process("a1")
    client = FakeClient(None, SolveApiError("invalid_payload", "Invalid solver input: nope", http_status=422))

    _run(runners(repository, client), ["a1"])

    assert repository.get_status("a1") is ProcessStatus.FAILED
    folder = storage.process_dir("a1")
    assert not (folder / PENDING_FILENAME).exists()
    record = json.loads((folder / ERROR_FILENAME).read_text(encoding="utf-8"))
    assert record["http_status"] == 422
    assert record["error_type"] == "invalid_payload"


def test_unexpected_exception_is_recorded_generically(repository, add_process, runners):
    add_process("a1")
    client = FakeClient(None, RuntimeError("secret token=abc /internal/path"))
    runner = runners(repository, client)

    _run(runner, ["a1"])

    error = repository.read_error("a1")
    assert error["error_type"] == "unexpected_error"
    assert "secret" not in json.dumps(error)
    assert runner.active_ids() == frozenset()


def test_one_failure_does_not_stop_the_others(repository, add_process, solve_response, runners):
    ids = [add_process(n) for n in ("a1", "b2")]

    class Mixed:
        def solve(self, payload):
            if b'"n": 0' in payload:
                raise SolveApiError("service_error", "down", http_status=503)
            return solve_response

    _run(runners(repository, Mixed()), ids)

    statuses = {i.process_id: i.status for i in repository.list_processes()}
    assert statuses == {"a1": ProcessStatus.FAILED, "b2": ProcessStatus.SOLVED}


def test_resubmitting_an_active_process_is_skipped(repository, add_process, solve_response, runners):
    add_process("a1")
    client = GatedClient(solve_response)
    runner = runners(repository, client)
    _, futures = runner.submit(["a1"])

    second, more = runner.submit(["a1"])

    assert second.already_running == ("a1",)
    assert second.started == ()
    assert more == []
    client.release.set()
    wait(futures, timeout=10)
    assert client.peak == 1


def test_stale_pending_marker_is_recovered_by_rerun(repository, storage, add_process, solve_response, runners):
    add_process("a1")
    (storage.process_dir("a1") / PENDING_FILENAME).write_text("left by a crashed server")
    assert repository.get_status("a1") is ProcessStatus.RUNNING
    runner = runners(repository, FakeClient(solve_response))
    assert runner.active_ids() == frozenset()  # nothing live: the marker is stale

    submission = _run(runner, ["a1"])

    assert submission.started == ("a1",)
    assert repository.get_status("a1") is ProcessStatus.SOLVED


def test_rerun_replaces_previous_outcome(repository, add_process, solve_response, runners):
    add_process("a1")
    runner = runners(repository, FakeClient(None, SolveApiError("timeout", "slow")))
    _run(runner, ["a1"])
    assert repository.get_status("a1") is ProcessStatus.FAILED

    runner2 = runners(repository, FakeClient(solve_response))
    _run(runner2, ["a1"])

    assert repository.get_status("a1") is ProcessStatus.SOLVED
    assert repository.read_error("a1") is None


def test_unknown_and_invalid_ids_are_reported(repository, add_process, solve_response, runners):
    add_process("a1")
    client = FakeClient(solve_response)

    submission = _run(runners(repository, client), ["ghost", "../evil", "a1", "a1"])

    assert submission.started == ("a1",)
    assert set(submission.not_found) == {"ghost", "../evil"}
    assert len(client.calls) == 1  # duplicate id in one submission runs once


def test_storage_failure_when_starting_is_reported_and_releases_id(
    repository, add_process, solve_response, runners, monkeypatch
):
    add_process("a1")
    runner = runners(repository, FakeClient(solve_response))

    def boom(_process_id):
        raise OSError("read-only")

    monkeypatch.setattr(repository, "begin_processing", boom)
    submission, futures = runner.submit(["a1"])

    assert submission.failed_to_start == ("a1",)
    assert futures == []
    assert runner.active_ids() == frozenset()
