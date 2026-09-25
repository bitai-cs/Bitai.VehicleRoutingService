"""Upload form logic without any Dash dependency: form values in, alert spec out."""

from __future__ import annotations

import base64
import binascii
import logging
from dataclasses import dataclass

from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.domain.exceptions import (
    DuplicatePayloadError,
    DuplicateProcessIdError,
    StorageCorruptedError,
    UploadError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    color: str  # Bootstrap contextual color
    message: str
    success: bool = False


def decode_upload_contents(contents: str) -> bytes:
    """Decode a ``dcc.Upload`` data URL (``data:<mime>;base64,<data>``)."""
    try:
        _, encoded = contents.split(",", 1)
        return base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("The uploaded file could not be read.") from exc


def handle_upload(
    service: UploadService, process_id: str | None, contents: str | None, filename: str | None
) -> UploadOutcome:
    if not contents:
        return UploadOutcome("warning", "Choose a JSON payload file to upload.")
    if filename and not filename.lower().endswith(".json"):
        return UploadOutcome("danger", "The file must have a .json extension.")
    try:
        raw = decode_upload_contents(contents)
        result = service.upload(process_id, raw)
    except DuplicatePayloadError as exc:
        return UploadOutcome(
            "warning",
            f"A similar payload already exists: process '{exc.existing_process_id}'. Nothing was saved.",
        )
    except DuplicateProcessIdError as exc:
        return UploadOutcome("danger", f"Process id '{exc.process_id}' is already in use. Choose another id.")
    except (UploadError, ValueError) as exc:
        return UploadOutcome("danger", str(exc))
    except StorageCorruptedError, OSError:
        logger.exception("Upload failed because of a storage problem")
        return UploadOutcome("danger", "The payload could not be stored because of a server storage problem.")
    return UploadOutcome("success", f"Payload saved as process '{result.process_id}'.", success=True)
