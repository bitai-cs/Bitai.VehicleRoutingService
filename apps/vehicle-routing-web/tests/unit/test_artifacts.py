import pytest

from vehicle_routing_web.domain import artifacts
from vehicle_routing_web.domain.artifacts import ProcessStatus, derive_status

RESULT = artifacts.RESULT_FILENAME
ERROR = artifacts.ERROR_FILENAME
PENDING = artifacts.PENDING_FILENAME


def test_filenames_use_the_agreed_names():
    assert RESULT == "solver-result.json"
    assert ERROR == "solver-error.json"
    assert PENDING == "solver-result.json.pending"


def test_pending_marker_name_is_derived_from_result_name():
    assert PENDING.removesuffix(".pending") == RESULT


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (set(), ProcessStatus.PENDING),
        ({"p-payload.json"}, ProcessStatus.PENDING),
        ({"p-payload.json", PENDING}, ProcessStatus.RUNNING),
        ({RESULT}, ProcessStatus.SOLVED),
        ({ERROR}, ProcessStatus.FAILED),
        # A marker always wins, so stale outcomes are never shown as current.
        ({PENDING, RESULT}, ProcessStatus.RUNNING),
        ({PENDING, ERROR}, ProcessStatus.RUNNING),
        ({PENDING, RESULT, ERROR}, ProcessStatus.RUNNING),
        # Leftover temp files are ignored.
        ({f"{RESULT}.tmp"}, ProcessStatus.PENDING),
    ],
)
def test_derive_status(files, expected):
    assert derive_status(files) is expected
