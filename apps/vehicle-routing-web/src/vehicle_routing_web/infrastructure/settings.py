"""Externalised, typed configuration (env vars prefixed ``VRW_`` or a ``.env`` file)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VRW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8050
    debug: bool = False
    log_level: str = "INFO"

    api_base_url: str = "http://localhost:8000"
    api_timeout_seconds: float = Field(default=300.0, gt=0)

    # Relative paths resolve against the process working directory.
    storage_dir: Path = Path("./storage")
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0)


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
