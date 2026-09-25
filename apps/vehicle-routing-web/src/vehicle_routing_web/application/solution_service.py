"""Loads and validates a solved process once, then serves it from a small server-side cache.

The cache is keyed by ``(process_id, result mtime, payload mtime)``, so a
re-run (new result file) can never serve a stale solution. Entries hold no
per-user data. Browsers only ever receive the process id and figures/tables
built from the cached solution, never the solution itself.
"""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError

from vehicle_routing_web.data.process_repository import ProcessRepository
from vehicle_routing_web.domain.artifacts import ProcessStatus
from vehicle_routing_web.domain.exceptions import StorageCorruptedError
from vehicle_routing_web.domain.metrics import compute_metrics
from vehicle_routing_web.domain.scenario import Scenario
from vehicle_routing_web.domain.solution import Solution

_CacheKey = tuple[str, int, int]


@dataclass(frozen=True, slots=True)
class SolutionLoad:
    status: ProcessStatus
    solution: Solution | None = None
    error: dict | None = None  # the stored solver-error.json record when status is FAILED


class SolutionService:
    def __init__(self, repository: ProcessRepository, cache_size: int = 8) -> None:
        self._repository = repository
        self._cache_size = max(1, cache_size)
        self._cache: OrderedDict[_CacheKey, Solution] = OrderedDict()
        self._lock = threading.Lock()

    def load(self, process_id: str) -> SolutionLoad:
        """Raises ``ProcessNotFoundError``, ``InvalidProcessIdError`` or ``StorageCorruptedError``."""
        status = self._repository.get_status(process_id)
        if status is ProcessStatus.FAILED:
            return SolutionLoad(status, error=self._repository.read_error(process_id))
        if status is not ProcessStatus.SOLVED:
            return SolutionLoad(status)

        version = self._repository.result_version(process_id)
        if version is None:  # changed between the two disk reads
            return SolutionLoad(self._repository.get_status(process_id))
        key: _CacheKey = (process_id, *version)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return SolutionLoad(status, cached)

        solution = self._build(process_id, version[0])
        with self._lock:
            self._cache[key] = solution
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return SolutionLoad(status, solution)

    def _build(self, process_id: str, result_mtime_ns: int) -> Solution:
        response = self._repository.read_result(process_id)
        if response is None:
            raise StorageCorruptedError("Stored solver result is no longer available.")
        try:
            scenario = Scenario.model_validate(json.loads(self._repository.read_payload_bytes(process_id)))
        except (ValueError, ValidationError) as exc:
            raise StorageCorruptedError("The stored payload does not match the expected scenario format.") from exc
        return Solution(
            process_id=process_id,
            response=response,
            scenario=scenario,
            metrics=compute_metrics(response),
            generated_at=datetime.fromtimestamp(result_mtime_ns / 1e9, tz=UTC),
        )
