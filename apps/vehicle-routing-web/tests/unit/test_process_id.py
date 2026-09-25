import pytest

from vehicle_routing_web.domain.exceptions import InvalidProcessIdError
from vehicle_routing_web.domain.process_id import MAX_PROCESS_ID_LENGTH, validate_process_id


@pytest.mark.parametrize("value", ["proc1", "Run_2026-09-24", "a", "0abc", "x" * MAX_PROCESS_ID_LENGTH])
def test_accepts_valid_ids(value):
    assert validate_process_id(value) == value


def test_trims_surrounding_whitespace():
    assert validate_process_id("  proc1 ") == "proc1"


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        "..",
        "../etc",
        "a/b",
        "a\\b",
        "C:\\temp",
        "C:x",
        "abc.json",
        ".hidden",
        "-leading",
        "_leading",
        "sp ace",
        "uni\u00e9",
        "x" * (MAX_PROCESS_ID_LENGTH + 1),
        "CON",
        "nul",
        "Com1",
        "a\x00b",
        "a\nb",
    ],
)
def test_rejects_invalid_ids(value):
    with pytest.raises(InvalidProcessIdError):
        validate_process_id(value)
