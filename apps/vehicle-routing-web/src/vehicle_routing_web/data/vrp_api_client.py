"""HTTP client for ``POST /api/v1/vrp/solve``.

Retry policy: the solve call is a pure computation (no side effects), so it
is safe to repeat, but only failures that are plausibly transient are
retried: connection failures and 502/503/504. Read timeouts are *not*
retried (a solve that already ran for the whole timeout would be repeated
for nothing), and neither are 4xx or a plain 500 (deterministic).

Every failure is mapped to :class:`SolveApiError` with a user-safe message;
response bodies and exception text are never copied through, except the
bounded ``detail`` of a 422 problem-details response from our own service.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import ValidationError

from vehicle_routing_web.domain.exceptions import SolveApiError
from vehicle_routing_web.domain.solve_response import SolveResponse

logger = logging.getLogger(__name__)

SOLVE_PATH = "/api/v1/vrp/solve"
RETRYABLE_STATUS = frozenset({502, 503, 504})
MAX_DETAIL_CHARS = 500


class VrpApiClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds, connect=10.0),
            transport=transport,
        )
        self._max_attempts = max(1, max_attempts)
        self._backoff = backoff_seconds
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def solve(self, payload_json: bytes) -> dict[str, Any]:
        """POST the payload bytes as-is and return the validated response JSON."""
        response = self._post_with_retries(payload_json)
        return self._parse(response)

    def _post_with_retries(self, payload_json: bytes) -> httpx.Response:
        for attempt in range(1, self._max_attempts + 1):
            last = attempt == self._max_attempts
            try:
                response = self._client.post(
                    SOLVE_PATH, content=payload_json, headers={"Content-Type": "application/json"}
                )
            except httpx.TimeoutException as exc:
                if isinstance(exc, httpx.ConnectTimeout) and not last:
                    self._pause(attempt, "connect timeout")
                    continue
                raise SolveApiError("timeout", "The solver service did not respond in time.") from exc
            except httpx.ConnectError as exc:
                if not last:
                    self._pause(attempt, "connect error")
                    continue
                raise SolveApiError("connection_error", "The solver service is unreachable.") from exc
            except httpx.HTTPError as exc:
                raise SolveApiError("transport_error", "Communication with the solver service failed.") from exc

            if response.status_code in RETRYABLE_STATUS and not last:
                self._pause(attempt, f"HTTP {response.status_code}")
                continue
            return response
        raise AssertionError("unreachable")  # pragma: no cover

    def _pause(self, attempt: int, reason: str) -> None:
        delay = self._backoff * 2 ** (attempt - 1)
        logger.warning("Solver call attempt %d failed (%s); retrying in %.1fs", attempt, reason, delay)
        self._sleep(delay)

    @staticmethod
    def _parse(response: httpx.Response) -> dict[str, Any]:
        status = response.status_code
        if status == 422:
            raise SolveApiError("invalid_payload", _problem_detail(response), http_status=status)
        if 400 <= status < 500:
            raise SolveApiError("request_rejected", f"The solver service rejected the request (HTTP {status}).", status)
        if status >= 500:
            raise SolveApiError("service_error", f"The solver service failed (HTTP {status}).", status)
        if status != 200:
            raise SolveApiError("unexpected_status", f"Unexpected response from solver (HTTP {status}).", status)

        try:
            data = response.json()
            SolveResponse.model_validate(data)
        except (ValueError, ValidationError) as exc:
            raise SolveApiError(
                "invalid_response", "The solver service returned a response in an unexpected format.", status
            ) from exc
        return data


def _problem_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError, AttributeError:
        detail = None
    if isinstance(detail, str) and detail.strip():
        return "Invalid solver input: " + detail.strip()[:MAX_DETAIL_CHARS]
    return "The solver service rejected the payload as invalid."
