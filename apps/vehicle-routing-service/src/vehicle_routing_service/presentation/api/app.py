"""FastAPI application factory: routing, CORS, and exception-handler wiring.

FastAPI is the HTTP delivery mechanism only; business logic lives in the
application/domain layers and is merely invoked from here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vehicle_routing_service.infrastructure.config.settings import get_settings
from vehicle_routing_service.presentation.api.exception_handlers import (
    register_exception_handlers,
)
from vehicle_routing_service.presentation.api.routes.health import (
    router as health_router,
)
from vehicle_routing_service.presentation.api.routes.vrp import router as vrp_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Vehicle Routing Service",
        version="0.1.0",
        description="Solves vehicle routing problems via OR-Tools.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(vrp_router, prefix="/api/v1/vrp", tags=["vrp"])

    return app


app = create_app()
