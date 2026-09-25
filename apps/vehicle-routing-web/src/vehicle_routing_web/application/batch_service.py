"""Batch solve orchestration: parallel, in-process, state kept on disk.

The runner holds no status of its own. It keeps only a set of ids that *this*
process is currently working on, used to refuse double submission and to
tell a live run from a stale ``.pending`` marker left by a crashed server.

Concurrency: at most ``max_workers`` solve calls run at once; further
submissions wait in the executor queue and already show as *running* (their
marker is written at submit time).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from vehicle_routing_web.data.process_repository import ProcessRepository
from vehicle_routing_web.domain.exceptions import InvalidProcessIdError, ProcessNotFoundError, SolveApiError
from vehicle_routing_web.domain.process_id import validate_process_id

logger = logging.getLogger(__name__)


class SolverClient(Protocol):
    def solve(self, payload_json: bytes) -> dict: ...


@dataclass(frozen=True, slots=True)
class BatchSubmission:
    started: tuple[str, ...] = ()
    already_running: tuple[str, ...] = ()
    not_found: tuple[str, ...] = ()
    failed_to_start: tuple[str, ...] = ()


class BatchRunner:
    def __init__(self, repository: ProcessRepository, client: SolverClient, max_workers: int) -> None:
        self._repository = repository
        self._client = client
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="solve")
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def active_ids(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._active)

    def submit(self, process_ids: Iterable[str]) -> tuple[BatchSubmission, list[Future[None]]]:
        """Mark each process as running and queue its solve.

        A process whose marker exists but that this server is not working on
        (a stale marker from a crash) is deliberately accepted and re-run.
        """
        started: list[str] = []
        already_running: list[str] = []
        not_found: list[str] = []
        failed_to_start: list[str] = []
        futures: list[Future[None]] = []

        for raw_id in dict.fromkeys(process_ids):  # de-duplicate, keep order
            try:
                process_id = validate_process_id(raw_id)
            except InvalidProcessIdError:
                not_found.append(str(raw_id))
                continue
            with self._lock:
                if process_id in self._active:
                    already_running.append(process_id)
                    continue
                self._active.add(process_id)
            try:
                self._repository.begin_processing(process_id)
            except ProcessNotFoundError:
                self._release(process_id)
                not_found.append(process_id)
                continue
            except OSError:
                logger.exception("Could not start processing of %s", process_id)
                self._release(process_id)
                failed_to_start.append(process_id)
                continue
            futures.append(self._executor.submit(self._run_one, process_id))
            started.append(process_id)

        submission = BatchSubmission(tuple(started), tuple(already_running), tuple(not_found), tuple(failed_to_start))
        return submission, futures

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)

    def _release(self, process_id: str) -> None:
        with self._lock:
            self._active.discard(process_id)

    def _run_one(self, process_id: str) -> None:
        try:
            try:
                payload = self._repository.read_payload_bytes(process_id)
                response = self._client.solve(payload)
            except SolveApiError as exc:
                self._repository.complete_failure(
                    process_id, error_type=exc.error_type, message=exc.message, http_status=exc.http_status
                )
                return
            except Exception:
                logger.exception("Unexpected failure while solving %s", process_id)
                self._repository.complete_failure(
                    process_id, error_type="unexpected_error", message="Unexpected error while processing."
                )
                return
            self._repository.complete_success(process_id, response)
        except Exception:
            # Writing the outcome failed; the marker stays, so the folder reads as running.
            logger.exception("Could not record the outcome for %s", process_id)
        finally:
            self._release(process_id)
