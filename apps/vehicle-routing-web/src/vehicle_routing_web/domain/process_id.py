"""Process-id validation.

The process id becomes a directory name and a file-name prefix, so it is
restricted to a conservative allowlist. This is the primary defence against
path traversal (``..``, separators, drive letters, ADS ``:``), and it also
avoids Windows reserved device names.
"""

from __future__ import annotations

import re

from vehicle_routing_web.domain.exceptions import InvalidProcessIdError

MAX_PROCESS_ID_LENGTH = 64

_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
)


def validate_process_id(value: str | None) -> str:
    """Return the trimmed process id, or raise :class:`InvalidProcessIdError`."""
    process_id = (value or "").strip()
    if not process_id:
        raise InvalidProcessIdError("Process id is required.")
    if len(process_id) > MAX_PROCESS_ID_LENGTH:
        raise InvalidProcessIdError(f"Process id must be at most {MAX_PROCESS_ID_LENGTH} characters.")
    if not _PATTERN.fullmatch(process_id):
        raise InvalidProcessIdError(
            "Process id may contain only letters, digits, '-' and '_' and must start with a letter or digit."
        )
    if process_id.upper() in _WINDOWS_RESERVED:
        raise InvalidProcessIdError("Process id is a reserved name.")
    return process_id
