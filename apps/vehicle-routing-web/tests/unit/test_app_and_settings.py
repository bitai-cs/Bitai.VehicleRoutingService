from pathlib import Path

import dash

from vehicle_routing_web.infrastructure.settings import AppSettings
from vehicle_routing_web.presentation.app import create_app


def test_settings_defaults(monkeypatch):
    for name in ("HOST", "PORT", "API_BASE_URL", "STORAGE_DIR"):
        monkeypatch.delenv(f"VRW_{name}", raising=False)
    settings = AppSettings(_env_file=None)

    assert settings.api_base_url == "http://localhost:8000"
    assert settings.storage_dir == Path("./storage")
    assert settings.port == 8050


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("VRW_API_BASE_URL", "http://solver:9000")
    monkeypatch.setenv("VRW_STORAGE_DIR", "/data/storage")

    settings = AppSettings(_env_file=None)

    assert settings.api_base_url == "http://solver:9000"
    assert settings.storage_dir == Path("/data/storage")


def test_app_registers_expected_routes():
    create_app()
    paths = {page.get("path_template") or page["path"] for page in dash.page_registry.values()}

    assert {"/", "/upload", "/batch", "/dashboard/<process_id>"} <= paths
