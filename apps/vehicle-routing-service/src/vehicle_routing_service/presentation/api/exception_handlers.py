"""Translation of domain/application exceptions into HTTP responses.

`solve_vrp` performs its own business-rule validation (mismatched list
lengths, inconsistent time windows, etc.) and signals violations by raising
plain `ValueError`. Per the architectural boundary, the domain must not know
about HTTP, so that translation happens here: any `ValueError` raised while
handling a request is reported as an RFC 7807 ("problem details") HTTP 422
response.

Note: registering a handler for the built-in `ValueError` is broad in
general, but appropriate for this service's current scope, which exposes a
single compute endpoint whose only realistic source of `ValueError` is
`solve_vrp`'s own input validation. If additional endpoints with different
`ValueError` semantics are added later, prefer introducing a dedicated
domain exception type (e.g. `InvalidSolverInputError(ValueError)`) and
narrowing this handler to it.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PROBLEM_DETAILS_MEDIA_TYPE = "application/problem+json"


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    problem = {
        "type": "https://vehicle-routing-service.local/errors/invalid-solver-input",
        "title": "Invalid VRP solver input",
        "status": 422,
        "detail": str(exc),
        "instance": str(request.url.path),
    }
    return JSONResponse(
        status_code=422,
        content=problem,
        media_type=PROBLEM_DETAILS_MEDIA_TYPE,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValueError, value_error_handler) # type: ignore[arg-type]
