"""File-system storage for payloads and the hash registry.

Layout::

    <storage_dir>/hashes.txt                       one "<sha256> <process_id>" per line
    <storage_dir>/payloads/<id>/<id>-payload.json  the payload exactly as uploaded

Concurrency: registration runs under a process-local lock, and the process
folder is created with an atomic ``mkdir`` so two processes cannot claim the
same id. The hash check-then-append is only guaranteed atomic within a single
server process; run one worker process (threads are fine) until a
cross-process lock is added.
"""

from __future__ import annotations

import contextlib
import shutil
import threading
from pathlib import Path

from vehicle_routing_web.domain.exceptions import (
    DuplicatePayloadError,
    DuplicateProcessIdError,
    StorageCorruptedError,
)
from vehicle_routing_web.domain.process_id import validate_process_id

HASHES_FILENAME = "hashes.txt"
PAYLOADS_DIRNAME = "payloads"


class FileStorage:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._lock = threading.Lock()

    @property
    def hashes_path(self) -> Path:
        return self._root / HASHES_FILENAME

    @property
    def payloads_dir(self) -> Path:
        return self._root / PAYLOADS_DIRNAME

    def process_dir(self, process_id: str) -> Path:
        """Directory for a process id, guaranteed to live inside ``payloads_dir``."""
        validate_process_id(process_id)
        base = self.payloads_dir.resolve()
        target = (base / process_id).resolve()
        if target.parent != base:
            raise ValueError("Resolved process path escapes the payloads directory.")
        return target

    def payload_path(self, process_id: str) -> Path:
        return self.process_dir(process_id) / f"{process_id}-payload.json"

    def read_registry(self) -> dict[str, str]:
        """Return ``{hash: process_id}``. A missing file is an empty registry."""
        try:
            text = self.hashes_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        registry: dict[str, str] = {}
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 2:
                raise StorageCorruptedError(f"Malformed registry entry at line {line_no}.")
            registry[parts[0]] = parts[1]
        return registry

    def add_payload(self, process_id: str, payload_hash: str, raw_payload: bytes) -> Path:
        """Atomically register a new payload; return the saved payload path.

        Raises :class:`DuplicatePayloadError` or :class:`DuplicateProcessIdError`
        without touching disk. If writing fails midway the new folder is removed
        and no registry entry is left behind (the registry line is written last).
        """
        target_dir = self.process_dir(process_id)
        with self._lock:
            registry = self.read_registry()
            if payload_hash in registry:
                raise DuplicatePayloadError(payload_hash, registry[payload_hash])
            if process_id in registry.values():
                raise DuplicateProcessIdError(process_id)

            self.payloads_dir.mkdir(parents=True, exist_ok=True)
            try:
                target_dir.mkdir(exist_ok=False)
            except FileExistsError as exc:
                raise DuplicateProcessIdError(process_id) from exc

            payload_file = target_dir / f"{process_id}-payload.json"
            try:
                payload_file.write_bytes(raw_payload)
                with self.hashes_path.open("a", encoding="utf-8", newline="\n") as fh:
                    fh.write(f"{payload_hash} {process_id}\n")
            except BaseException:
                shutil.rmtree(target_dir, ignore_errors=True)
                with contextlib.suppress(OSError):
                    self._remove_registry_line(payload_hash, process_id)
                raise
            return payload_file

    def _remove_registry_line(self, payload_hash: str, process_id: str) -> None:
        entry = f"{payload_hash} {process_id}"
        lines = self.hashes_path.read_text(encoding="utf-8").splitlines()
        kept = [ln for ln in lines if ln.strip() != entry]
        if len(kept) != len(lines):
            self.hashes_path.write_text("".join(f"{ln}\n" for ln in kept), encoding="utf-8", newline="\n")
