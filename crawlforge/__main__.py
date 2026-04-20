"""
crawlforge.__main__
~~~~~~~~~~~~~~~~~~~~
CLI entrypoint: `python -m crawlforge`
No logic here — delegates to uvicorn.
"""

from __future__ import annotations

import uvicorn

from crawlforge.config.settings import get_settings


def main() -> None:
    """Start the CrawlForge API server."""
    settings = get_settings()
    uvicorn.run(
        "crawlforge.api.app:create_app",
        factory=True,
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
