"""Payload parsing and content hashing.

Hashing choice: **canonical JSON**, not raw bytes.

The payload is parsed, then re-serialised with sorted keys, no insignificant
whitespace and UTF-8 encoding, and the SHA-256 of that is the identity. Two
uploads that differ only in key order, indentation, line endings or BOM
therefore count as the same payload, which is what "similar payload" means
for de-duplication. Raw-byte hashing would miss all of those.

Known, accepted limits: array order is significant, and ``1`` and ``1.0``
are different values. The original uploaded bytes are what gets stored, so
the hash only decides identity and never alters the payload.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from vehicle_routing_web.domain.exceptions import InvalidPayloadError


def _reject_constant(name: str) -> Any:
    raise InvalidPayloadError(f"Payload contains non-standard JSON constant '{name}'.")


def parse_payload(raw: bytes) -> dict[str, Any]:
    """Parse uploaded bytes into a JSON object, or raise :class:`InvalidPayloadError`."""
    try:
        data = json.loads(raw, parse_constant=_reject_constant)
    except InvalidPayloadError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InvalidPayloadError("Payload is not valid JSON.") from exc
    if not isinstance(data, dict):
        raise InvalidPayloadError("Payload must be a JSON object.")
    return data


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """SHA-256 hex digest of the canonical JSON form of ``payload``."""
    return hashlib.sha256(canonical_json(payload)).hexdigest()
