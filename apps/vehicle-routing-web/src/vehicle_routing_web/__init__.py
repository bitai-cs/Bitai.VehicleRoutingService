def main() -> None:
    """Entry point for the `vehicle-routing-web` console script.

    Serves the Dash app using externalised settings (`VRW_HOST`, `VRW_PORT`, ...).
    """
    from vehicle_routing_web.infrastructure.settings import get_settings
    from vehicle_routing_web.presentation.app import create_app

    settings = get_settings()
    create_app().run(host=settings.host, port=settings.port, debug=settings.debug)
