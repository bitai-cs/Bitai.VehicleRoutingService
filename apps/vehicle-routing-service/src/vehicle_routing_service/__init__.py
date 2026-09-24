def main() -> None:
    """Entry point for the `vehicle-routing-service` console script.

    Launches the FastAPI app with uvicorn, using externalized settings
    (`VRS_HOST`, `VRS_PORT`, ...). Equivalent to running:

        uvicorn vehicle_routing_service.presentation.api.app:app --host <host> --port <port>
    """
    import uvicorn

    from vehicle_routing_service.infrastructure.config.settings import get_settings

    settings = get_settings()
    uvicorn.run(
        "vehicle_routing_service.presentation.api.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
