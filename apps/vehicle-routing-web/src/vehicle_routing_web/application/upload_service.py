"""Upload use case: validate, hash, de-duplicate, persist."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vehicle_routing_web.data.storage import FileStorage
from vehicle_routing_web.domain.exceptions import PayloadTooLargeError
from vehicle_routing_web.domain.payload_hash import compute_payload_hash, parse_payload
from vehicle_routing_web.domain.process_id import validate_process_id


@dataclass(frozen=True, slots=True)
class UploadResult:
    process_id: str
    payload_hash: str
    payload_path: Path


class UploadService:
    def __init__(self, storage: FileStorage, max_upload_bytes: int) -> None:
        self._storage = storage
        self._max_upload_bytes = max_upload_bytes

    def upload(self, process_id: str | None, raw_payload: bytes) -> UploadResult:
        """Store a new payload.

        Raises a subclass of :class:`~vehicle_routing_web.domain.exceptions.UploadError`
        for every expected failure (bad id, bad JSON, too large, duplicate hash,
        duplicate id).
        """
        valid_id = validate_process_id(process_id)
        if len(raw_payload) > self._max_upload_bytes:
            raise PayloadTooLargeError(f"Payload exceeds the {self._max_upload_bytes} byte limit.")
        payload_hash = compute_payload_hash(parse_payload(raw_payload))
        path = self._storage.add_payload(valid_id, payload_hash, raw_payload)
        return UploadResult(process_id=valid_id, payload_hash=payload_hash, payload_path=path)
