"""
crawlforge.api.routes.health
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Health-check endpoint — lightweight, no external deps.
"""

from __future__ import annotations

from fastapi import APIRouter

from crawlforge import __version__
from crawlforge.config.settings import get_settings
from crawlforge.models.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness check — always returns 200 if the process is up."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.app_env,
    )
