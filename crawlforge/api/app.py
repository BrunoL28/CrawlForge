"""
crawlforge.api.app
~~~~~~~~~~~~~~~~~~~
FastAPI application factory.
No business logic here — just wiring and lifecycle management.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from crawlforge import __version__
from crawlforge.api.routes import health
from crawlforge.config.settings import get_settings
from crawlforge.logger.setup import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle hooks."""
    settings = get_settings()
    setup_logger(settings)
    logger.info(
        "🚀 {} v{} starting — env={}",
        settings.app_name, __version__, settings.app_env,
    )
    yield
    logger.info("👋 {} shutting down", settings.app_name)


def create_app() -> FastAPI:
    """Build and return the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Professional web scraping system powered by crawl4ai",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────
    app.include_router(health.router)

    return app
