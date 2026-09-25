"""Names of the per-process files and the status derived from them.

These constants are the single source of truth for on-disk names. If the
result file needs to be renamed (for example ``solve-result.json``), change
``RESULT_FILENAME`` only; the marker name is derived from it.

Process status is derived purely from which files exist in the process
folder (see :func:`derive_status`); there is no other status store.
"""

from __future__ import annotations

from collections.abc import Collection
from enum import StrEnum

RESULT_FILENAME = "solver-result.json"
ERROR_FILENAME = "solver-error.json"
PENDING_FILENAME = f"{RESULT_FILENAME}.pending"


def payload_filename(process_id: str) -> str:
    return f"{process_id}-payload.json"


class ProcessStatus(StrEnum):
    PENDING = "pending"  # not processed yet
    RUNNING = "running"
    SOLVED = "solved"
    FAILED = "failed"


def derive_status(filenames: Collection[str]) -> ProcessStatus:
    """Map the set of file names in a process folder to a status.

    Precedence: the pending marker wins over everything. A marker together
    with a result/error file is therefore reported as running, never as
    solved or failed, so a stale result can not be shown as current. Result
    wins over error only if both exist (which the writers never produce).
    """
    if PENDING_FILENAME in filenames:
        return ProcessStatus.RUNNING
    if RESULT_FILENAME in filenames:
        return ProcessStatus.SOLVED
    if ERROR_FILENAME in filenames:
        return ProcessStatus.FAILED
    return ProcessStatus.PENDING
