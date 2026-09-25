"""Per-process state on disk: listing, status and the solve marker/result/error files.

Order of operations (chosen so a crash never yields an ambiguous state):

* start:   1. create ``<result>.pending``   2. delete old result and error files
* success: 1. atomically write the result   2. delete the pending marker
* failure: 1. atomically write the error    2. delete the pending marker

The pending marker always exists while any other artifact might be stale or
not yet finalised, and :func:`derive_status` gives it precedence, so after a
crash at any point the folder reads as *running* (never as a stale *solved*
or *failed*). Re-running clears the leftovers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from vehicle_routing_web.data.storage import FileStorage
from vehicle_routing_web.domain.artifacts import (
    ERROR_FILENAME,
    PENDING_FILENAME,
    RESULT_FILENAME,
    ProcessStatus,
    derive_status,
    payload_filename,
)
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, StorageCorruptedError
from vehicle_routing_web.domain.process_id import validate_process_id
from vehicle_routing_web.domain.solve_response import SolveResponse


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    process_id: str
    status: ProcessStatus


def _write_json_atomic(path: Path, data: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


class ProcessRepository:
    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    # -- queries (always read the disk; there is no cache) -------------------

    def list_processes(self) -> list[ProcessInfo]:
        base = self._storage.payloads_dir
        if not base.is_dir():
            return []
        infos: list[ProcessInfo] = []
        for entry in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir():
                continue
            try:
                process_id = validate_process_id(entry.name)
            except InvalidProcessIdError:
                continue
            if not (entry / payload_filename(process_id)).is_file():
                continue
            infos.append(ProcessInfo(process_id, self._status_of(entry)))
        return infos

    def get_status(self, process_id: str) -> ProcessStatus:
        return self._status_of(self._existing_dir(process_id))

    def read_payload_bytes(self, process_id: str) -> bytes:
        path = self._existing_dir(process_id) / payload_filename(process_id)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise ProcessNotFoundError(process_id) from exc

    def read_result(self, process_id: str) -> SolveResponse | None:
        """The validated result, or ``None`` unless the status is solved."""
        folder = self._existing_dir(process_id)
        if self._status_of(folder) is not ProcessStatus.SOLVED:
            return None
        try:
            return SolveResponse.model_validate_json((folder / RESULT_FILENAME).read_bytes())
        except (OSError, ValidationError) as exc:
            raise StorageCorruptedError("Stored solver result is unreadable.") from exc

    def result_version(self, process_id: str) -> tuple[int, int] | None:
        """``(result mtime_ns, payload mtime_ns)`` when solved, else ``None``. Cheap cache key."""
        folder = self._existing_dir(process_id)
        if self._status_of(folder) is not ProcessStatus.SOLVED:
            return None
        try:
            return (
                (folder / RESULT_FILENAME).stat().st_mtime_ns,
                (folder / payload_filename(process_id)).stat().st_mtime_ns,
            )
        except OSError:
            return None

    def read_error(self, process_id: str) -> dict[str, Any] | None:
        """The error record, or ``None`` unless the status is failed."""
        folder = self._existing_dir(process_id)
        if self._status_of(folder) is not ProcessStatus.FAILED:
            return None
        try:
            data = json.loads((folder / ERROR_FILENAME).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StorageCorruptedError("Stored solver error is unreadable.") from exc
        return data if isinstance(data, dict) else None

    # -- state transitions ---------------------------------------------------

    def begin_processing(self, process_id: str) -> None:
        """Mark the process as running and discard any previous outcome."""
        folder = self._existing_dir(process_id)
        (folder / PENDING_FILENAME).write_text(_now_iso(), encoding="utf-8")  # 1. marker first
        for name in (RESULT_FILENAME, ERROR_FILENAME):  # 2. then drop stale outcome
            (folder / name).unlink(missing_ok=True)

    def complete_success(self, process_id: str, response: dict[str, Any]) -> None:
        folder = self._existing_dir(process_id)
        _write_json_atomic(folder / RESULT_FILENAME, response)  # 1. outcome
        (folder / PENDING_FILENAME).unlink(missing_ok=True)  # 2. release marker

    def complete_failure(
        self, process_id: str, *, error_type: str, message: str, http_status: int | None = None
    ) -> None:
        """Record a user-safe failure: no stack traces, no secrets."""
        folder = self._existing_dir(process_id)
        record = {
            "http_status": http_status,
            "error_type": error_type,
            "message": message,
            "occurred_at": _now_iso(),
        }
        _write_json_atomic(folder / ERROR_FILENAME, record)
        (folder / PENDING_FILENAME).unlink(missing_ok=True)

    # -- helpers ---------------------------------------------------------------

    def _existing_dir(self, process_id: str) -> Path:
        folder = self._storage.process_dir(process_id)  # validates the id
        if not folder.is_dir():
            raise ProcessNotFoundError(process_id)
        return folder

    @staticmethod
    def _status_of(folder: Path) -> ProcessStatus:
        return derive_status({p.name for p in folder.iterdir()})


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
