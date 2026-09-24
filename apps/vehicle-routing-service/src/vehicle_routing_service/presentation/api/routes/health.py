from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Is the process alive?"""
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """Can this instance safely receive traffic?

    This service has no external dependencies (no database, no cache, no
    downstream services), so readiness is equivalent to liveness today.
    """
    return {"status": "ok"}
