"""Batch page view-model: rows, column definitions and messages, free of Dash callbacks."""

from __future__ import annotations

import logging
from collections.abc import Collection, Iterable
from typing import Any

from vehicle_routing_web.application.batch_service import BatchSubmission
from vehicle_routing_web.data.process_repository import ProcessRepository
from vehicle_routing_web.domain.artifacts import ProcessStatus
from vehicle_routing_web.domain.exceptions import ProcessNotFoundError, StorageCorruptedError

logger = logging.getLogger(__name__)

STALE_NOTE = "No active job on this server (possibly interrupted). Run again to recover."
MAX_NOTE_CHARS = 200

COLUMN_DEFS: list[dict[str, Any]] = [
    {"field": "process_id", "headerName": "Process ID", "filter": True, "flex": 1, "minWidth": 180},
    {
        "field": "status",
        "headerName": "Status",
        "filter": True,
        "width": 140,
        "cellClassRules": {
            "text-success fw-semibold": "params.value === 'solved'",
            "text-danger fw-semibold": "params.value === 'failed'",
            "text-primary fw-semibold": "params.value === 'running'",
            "text-secondary": "params.value === 'pending'",
        },
    },
    {"field": "note", "headerName": "Details", "flex": 3, "minWidth": 240, "tooltipField": "note"},
]

GRID_OPTIONS: dict[str, Any] = {
    "rowSelection": {"mode": "multiRow", "checkboxes": True, "headerCheckbox": True, "enableClickSelection": False},
    "animateRows": False,
    "overlayNoRowsTemplate": "No payloads uploaded yet. Use the Upload page first.",
}


def build_rows(repository: ProcessRepository, active_ids: Collection[str]) -> list[dict[str, str]]:
    """One row per process folder; the status is read from disk on every call."""
    rows: list[dict[str, str]] = []
    for info in repository.list_processes():
        rows.append(
            {"process_id": info.process_id, "status": info.status.value, "note": _note(repository, info, active_ids)}
        )
    return rows


def _note(repository: ProcessRepository, info: Any, active_ids: Collection[str]) -> str:
    if info.status is ProcessStatus.RUNNING and info.process_id not in active_ids:
        return STALE_NOTE
    if info.status is ProcessStatus.FAILED:
        try:
            error = repository.read_error(info.process_id) or {}
        except StorageCorruptedError, ProcessNotFoundError:
            return "Error details are unreadable."
        return str(error.get("message", ""))[:MAX_NOTE_CHARS]
    return ""


def selected_ids(selected_rows: Iterable[dict[str, Any]] | None) -> list[str]:
    return [str(row["process_id"]) for row in selected_rows or [] if row.get("process_id")]


def describe_submission(submission: BatchSubmission) -> tuple[str, str]:
    """Return ``(bootstrap color, message)`` for the outcome of a Solve click."""
    parts: list[str] = []
    if submission.started:
        parts.append(f"Started {len(submission.started)} process(es): {', '.join(submission.started)}.")
    if submission.already_running:
        parts.append(f"Already running here, skipped: {', '.join(submission.already_running)}.")
    if submission.not_found:
        parts.append(f"Not found: {', '.join(submission.not_found)}.")
    if submission.failed_to_start:
        parts.append(f"Could not start (storage problem): {', '.join(submission.failed_to_start)}.")
    if submission.not_found or submission.failed_to_start:
        color = "danger"
    elif submission.already_running:
        color = "warning"
    else:
        color = "success"
    return color, " ".join(parts) or "Nothing to do."
