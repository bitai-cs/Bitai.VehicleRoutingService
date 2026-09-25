"""Composition root: builds the long-lived, stateless-per-user services once.

These objects hold no user/session data (status lives on disk), so sharing
them process-wide is safe.
"""

from __future__ import annotations

from functools import lru_cache

from vehicle_routing_web.application.batch_service import BatchRunner
from vehicle_routing_web.application.solution_service import SolutionService
from vehicle_routing_web.application.upload_service import UploadService
from vehicle_routing_web.data.process_repository import ProcessRepository
from vehicle_routing_web.data.storage import FileStorage
from vehicle_routing_web.data.vrp_api_client import VrpApiClient
from vehicle_routing_web.infrastructure.settings import get_settings


@lru_cache
def get_storage() -> FileStorage:
    return FileStorage(get_settings().storage_dir)


@lru_cache
def get_repository() -> ProcessRepository:
    return ProcessRepository(get_storage())


@lru_cache
def get_solution_service() -> SolutionService:
    return SolutionService(get_repository())


@lru_cache
def get_upload_service() -> UploadService:
    return UploadService(get_storage(), get_settings().max_upload_bytes)


@lru_cache
def get_batch_runner() -> BatchRunner:
    settings = get_settings()
    client = VrpApiClient(settings.api_base_url, settings.api_timeout_seconds)
    return BatchRunner(get_repository(), client, settings.max_concurrent_solves)
