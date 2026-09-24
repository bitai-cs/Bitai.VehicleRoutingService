"""Externalized, typed application configuration.

Values are read from environment variables (prefixed with ``VRS_``) or an
optional ``.env`` file. No secrets are required for this stateless,
compute-only service today, but the settings module gives the app a single,
typed place to grow configuration (e.g. auth, observability exporters) later
without leaking configuration concerns into business code.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VRS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
