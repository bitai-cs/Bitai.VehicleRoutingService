import json
from pathlib import Path

import pytest

from vehicle_routing_web.domain.artifacts import ERROR_FILENAME, PENDING_FILENAME, RESULT_FILENAME, ProcessStatus
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, StorageCorruptedError


def _folder(storage, process_id) -> Path:
    return storage.process_dir(process_id)


def test_list_processes_reports_status_from_files(repository, storage, add_process):
    for name in ("alpha", "bravo", "charlie", "delta"):
        add_process(name)
    (_folder(storage, "bravo") / PENDING_FILENAME).write_text("x")
    (_folder(storage, "charlie") / RESULT_FILENAME).write_text("{}")
    (_folder(storage, "delta") / ERROR_FILENAME).write_text("{}")

    statuses = {info.process_id: info.status for info in repository.list_processes()}

    assert statuses == {
        "alpha": ProcessStatus.PENDING,
        "bravo": ProcessStatus.RUNNING,
        "charlie": ProcessStatus.SOLVED,
        "delta": ProcessStatus.FAILED,
    }


def test_list_is_empty_without_storage(repository):
    assert repository.list_processes() == []


def test_list_ignores_foreign_folders_and_files(repository, storage, add_process):
    add_process("good")
    (storage.payloads_dir / "no-payload").mkdir()
    (storage.payloads_dir / "bad name").mkdir()
    (storage.payloads_dir / "stray.txt").write_text("x")

    assert [i.process_id for i in repository.list_processes()] == ["good"]


def test_list_reads_the_disk_every_time(repository, storage, add_process):
    add_process("alpha")
    assert repository.list_processes()[0].status is ProcessStatus.PENDING
    (_folder(storage, "alpha") / RESULT_FILENAME).write_text("{}")
    assert repository.list_processes()[0].status is ProcessStatus.SOLVED


def test_begin_processing_creates_marker_and_removes_old_outcome(repository, storage, add_process):
    add_process("alpha")
    folder = _folder(storage, "alpha")
    (folder / RESULT_FILENAME).write_text("{}")
    (folder / ERROR_FILENAME).write_text("{}")

    repository.begin_processing("alpha")

    assert (folder / PENDING_FILENAME).is_file()
    assert not (folder / RESULT_FILENAME).exists()
    assert not (folder / ERROR_FILENAME).exists()
    assert repository.get_status("alpha") is ProcessStatus.RUNNING


def test_begin_creates_marker_before_deleting_old_outcome(repository, storage, add_process, monkeypatch):
    """Crash between the two steps must read as running, never as the stale result."""
    add_process("alpha")
    folder = _folder(storage, "alpha")
    (folder / RESULT_FILENAME).write_text("{}")

    def crash(self, missing_ok=False):
        raise KeyboardInterrupt("simulated crash")

    monkeypatch.setattr(Path, "unlink", crash)
    with pytest.raises(KeyboardInterrupt):
        repository.begin_processing("alpha")
    monkeypatch.undo()

    assert (folder / PENDING_FILENAME).exists()
    assert (folder / RESULT_FILENAME).exists()  # stale file still there ...
    assert repository.get_status("alpha") is ProcessStatus.RUNNING  # ... but not shown as current
    assert repository.read_result("alpha") is None


def test_success_writes_result_then_releases_marker(repository, storage, add_process, solve_response):
    add_process("alpha")
    repository.begin_processing("alpha")

    repository.complete_success("alpha", solve_response)

    folder = _folder(storage, "alpha")
    assert not (folder / PENDING_FILENAME).exists()
    assert not (folder / ERROR_FILENAME).exists()
    assert json.loads((folder / RESULT_FILENAME).read_text(encoding="utf-8")) == solve_response
    assert repository.get_status("alpha") is ProcessStatus.SOLVED
    result = repository.read_result("alpha")
    assert result is not None
    assert result.service_level_pct == pytest.approx(5 / 6 * 100)


def test_crash_after_result_before_marker_release_reads_as_running(
    repository, storage, add_process, solve_response, monkeypatch
):
    add_process("alpha")
    repository.begin_processing("alpha")

    def crash(self, missing_ok=False):
        raise KeyboardInterrupt("simulated crash")

    monkeypatch.setattr(Path, "unlink", crash)
    with pytest.raises(KeyboardInterrupt):
        repository.complete_success("alpha", solve_response)
    monkeypatch.undo()

    assert repository.get_status("alpha") is ProcessStatus.RUNNING
    assert repository.read_result("alpha") is None


def test_success_leaves_no_temp_file(repository, storage, add_process, solve_response):
    add_process("alpha")
    repository.begin_processing("alpha")
    repository.complete_success("alpha", solve_response)

    assert not list(_folder(storage, "alpha").glob("*.tmp"))


def test_failure_writes_user_safe_error_and_releases_marker(repository, storage, add_process):
    add_process("alpha")
    repository.begin_processing("alpha")

    repository.complete_failure("alpha", error_type="invalid_payload", message="Bad input", http_status=422)

    folder = _folder(storage, "alpha")
    assert not (folder / PENDING_FILENAME).exists()
    assert not (folder / RESULT_FILENAME).exists()
    record = json.loads((folder / ERROR_FILENAME).read_text(encoding="utf-8"))
    assert set(record) == {"http_status", "error_type", "message", "occurred_at"}
    assert record["http_status"] == 422
    assert record["error_type"] == "invalid_payload"
    assert record["message"] == "Bad input"
    assert record["occurred_at"].endswith("+00:00")
    assert repository.get_status("alpha") is ProcessStatus.FAILED
    assert repository.read_error("alpha") == record


def test_failure_without_http_status_stores_null(repository, add_process):
    add_process("alpha")
    repository.begin_processing("alpha")
    repository.complete_failure("alpha", error_type="timeout", message="slow")

    assert repository.read_error("alpha")["http_status"] is None


def test_reprocessing_after_success_and_failure(repository, add_process, solve_response):
    add_process("alpha")
    repository.begin_processing("alpha")
    repository.complete_failure("alpha", error_type="timeout", message="slow")
    repository.begin_processing("alpha")
    assert repository.read_error("alpha") is None  # error not shown while running
    repository.complete_success("alpha", solve_response)
    repository.begin_processing("alpha")

    assert repository.get_status("alpha") is ProcessStatus.RUNNING
    assert repository.read_result("alpha") is None


def test_read_result_and_error_are_none_for_other_statuses(repository, add_process):
    add_process("alpha")

    assert repository.read_result("alpha") is None
    assert repository.read_error("alpha") is None


def test_corrupt_result_raises_storage_error(repository, storage, add_process):
    add_process("alpha")
    (_folder(storage, "alpha") / RESULT_FILENAME).write_text("{not json")

    with pytest.raises(StorageCorruptedError):
        repository.read_result("alpha")


def test_result_missing_required_fields_raises_storage_error(repository, storage, add_process):
    add_process("alpha")
    (_folder(storage, "alpha") / RESULT_FILENAME).write_text('{"status": "OPTIMAL"}')

    with pytest.raises(StorageCorruptedError):
        repository.read_result("alpha")


def test_unknown_and_invalid_ids(repository):
    with pytest.raises(ProcessNotFoundError):
        repository.begin_processing("ghost")
    with pytest.raises(InvalidProcessIdError):
        repository.get_status("../evil")
    with pytest.raises(ProcessNotFoundError):
        repository.read_payload_bytes("ghost")


def test_read_payload_bytes_returns_uploaded_content(repository, add_process):
    add_process("alpha")

    assert repository.read_payload_bytes("alpha").startswith(b'{"n"')
