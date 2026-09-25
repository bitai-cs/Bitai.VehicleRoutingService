"""Domain errors for the upload workflow.

Messages are user-safe: they never contain filesystem paths or raw payload content.
"""

from __future__ import annotations


class UploadError(Exception):
    """Base class for all expected, user-facing upload failures."""


class InvalidProcessIdError(UploadError):
    """The process id does not satisfy the allowed format."""


class InvalidPayloadError(UploadError):
    """The uploaded bytes are not an acceptable JSON payload."""


class PayloadTooLargeError(UploadError):
    """The uploaded payload exceeds the configured size limit."""


class DuplicatePayloadError(UploadError):
    """A payload with the same content hash is already registered."""

    def __init__(self, payload_hash: str, existing_process_id: str) -> None:
        super().__init__(f"A similar payload already exists (process '{existing_process_id}').")
        self.payload_hash = payload_hash
        self.existing_process_id = existing_process_id


class DuplicateProcessIdError(UploadError):
    """The process id is already in use."""

    def __init__(self, process_id: str) -> None:
        super().__init__(f"Process id '{process_id}' already exists.")
        self.process_id = process_id


class ProcessNotFoundError(Exception):
    """No process folder/payload exists for the given id."""


class SolveApiError(Exception):
    """A failed call to the solver API, already mapped to user-safe fields.

    ``message`` never contains stack traces, URLs with credentials or raw
    response bodies.
    """

    def __init__(self, error_type: str, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.http_status = http_status


class StorageCorruptedError(Exception):
    """The on-disk registry is unreadable. Operational error, not a user mistake."""
