import base64
import json

import pytest

from tests.factories import make_payload_dict
from vehicle_routing_web.application.batch_service import BatchSubmission
from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.domain.artifacts import PENDING_FILENAME, RESULT_FILENAME
from vehicle_routing_web.presentation import batch_view
from vehicle_routing_web.presentation.app import create_app
from vehicle_routing_web.presentation.upload_handler import decode_upload_contents, handle_upload


@pytest.fixture
def dashboard(isolated_container):
    """The dashboard page module; pages can only be imported once an app exists."""
    create_app()
    from vehicle_routing_web.presentation.pages import dashboard as module

    return module


def _contents(raw: bytes) -> str:
    return "data:application/json;base64," + base64.b64encode(raw).decode()


@pytest.fixture
def service(storage):
    return UploadService(storage, max_upload_bytes=1000)


def test_decode_upload_contents_roundtrip():
    assert decode_upload_contents(_contents(b'{"a":1}')) == b'{"a":1}'


@pytest.mark.parametrize("bad", ["", "no-comma", "data:x;base64,@@@@"])
def test_decode_rejects_garbage(bad):
    with pytest.raises(ValueError, match="could not be read"):
        decode_upload_contents(bad)


def test_upload_success_alert(service, storage):
    outcome = handle_upload(service, "run1", _contents(b'{"a": 1}'), "p.json")

    assert (outcome.color, outcome.success) == ("success", True)
    assert storage.payload_path("run1").is_file()


def test_upload_duplicate_hash_warns_and_names_existing_process(service):
    handle_upload(service, "run1", _contents(b'{"a": 1}'), "p.json")

    outcome = handle_upload(service, "run2", _contents(b'{ "a" : 1 }'), "p.json")

    assert outcome.color == "warning"
    assert "similar payload already exists" in outcome.message
    assert "run1" in outcome.message


def test_upload_duplicate_process_id_is_an_error(service):
    handle_upload(service, "run1", _contents(b'{"a": 1}'), "p.json")

    outcome = handle_upload(service, "run1", _contents(b'{"a": 2}'), "p.json")

    assert outcome.color == "danger"
    assert "already in use" in outcome.message


@pytest.mark.parametrize(
    ("process_id", "contents", "filename", "color"),
    [
        ("run1", None, None, "warning"),
        ("run1", _contents(b"{}"), "notes.txt", "danger"),
        ("", _contents(b"{}"), "p.json", "danger"),
        ("../x", _contents(b"{}"), "p.json", "danger"),
        ("run1", _contents(b"not json"), "p.json", "danger"),
        ("run1", "garbage", "p.json", "danger"),
        ("run1", _contents(b"{" + b" " * 2000 + b"}"), "p.json", "danger"),
    ],
)
def test_upload_rejections(service, process_id, contents, filename, color):
    assert handle_upload(service, process_id, contents, filename).color == color


def test_batch_rows_and_stale_note(repository, storage, add_process):
    for name in ("alpha", "bravo", "charlie"):
        add_process(name)
    (storage.process_dir("alpha") / PENDING_FILENAME).write_text("x")
    (storage.process_dir("bravo") / PENDING_FILENAME).write_text("x")
    repository.complete_failure("charlie", error_type="timeout", message="Solver too slow")

    rows = {r["process_id"]: r for r in batch_view.build_rows(repository, active_ids={"alpha"})}

    assert rows["alpha"] == {"process_id": "alpha", "status": "running", "note": ""}
    assert rows["bravo"]["note"] == batch_view.STALE_NOTE
    assert rows["charlie"] == {"process_id": "charlie", "status": "failed", "note": "Solver too slow"}


def test_grid_uses_process_id_as_row_identity():
    assert batch_view.COLUMN_DEFS[0]["field"] == "process_id"


def test_selected_ids():
    assert batch_view.selected_ids([{"process_id": "a"}, {"other": 1}, {"process_id": "b"}]) == ["a", "b"]
    assert batch_view.selected_ids(None) == []


def test_describe_submission_colors():
    assert batch_view.describe_submission(BatchSubmission(started=("a",)))[0] == "success"
    assert batch_view.describe_submission(BatchSubmission(already_running=("a",)))[0] == "warning"
    assert batch_view.describe_submission(BatchSubmission(not_found=("a",)))[0] == "danger"
    assert batch_view.describe_submission(BatchSubmission())[1] == "Nothing to do."


def test_dashboard_reads_the_result_file_constant(dashboard, solve_response):
    from vehicle_routing_web.presentation.container import get_repository, get_storage, get_upload_service

    get_upload_service().upload("run1", json.dumps(make_payload_dict()).encode())
    assert "not been solved" in str(dashboard.layout(process_id="run1"))

    get_repository().begin_processing("run1")
    assert "in progress" in str(dashboard.layout(process_id="run1"))

    get_repository().complete_success("run1", solve_response)
    assert (get_storage().process_dir("run1") / RESULT_FILENAME).is_file()
    page = str(dashboard.layout(process_id="run1"))
    assert "FEASIBLE" in page
    assert "83.3 %" in page


def test_dashboard_failed_invalid_and_missing(dashboard):
    from vehicle_routing_web.presentation.container import get_repository, get_upload_service

    get_upload_service().upload("run1", b'{"a": 1}')
    get_repository().begin_processing("run1")
    get_repository().complete_failure("run1", error_type="timeout", message="Too slow", http_status=None)

    assert "Too slow" in str(dashboard.layout(process_id="run1"))
    assert "Invalid process id" in str(dashboard.layout(process_id="../x"))
    assert "Process not found" in str(dashboard.layout(process_id="ghost"))
