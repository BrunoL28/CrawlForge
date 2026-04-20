"""
scripts/crawl.py
~~~~~~~~~~~~~~~~~
CLI crawler invoked by `make crawl url=<URL>`.

Usage:
    python scripts/crawl.py https://example.com
    python scripts/crawl.py https://example.com --strategy css
"""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")  # Allow running from project root without installing


async def main(url: str) -> None:
    from crawlforge.config.settings import get_settings
    from crawlforge.core.engine import CrawlerEngine
    from crawlforge.logger.setup import setup_logger
    from crawlforge.models.schemas import CrawlJob

    settings = get_settings()
    setup_logger(settings)

    engine = CrawlerEngine(settings)
    job = CrawlJob(url=url)
    result = await engine.execute(job)

    print("─" * 60)
    print(f"Success:   {result.success}")
    print(f"Duration:  {result.duration_ms:.0f} ms")
    print(f"Bytes:     {result.bytes_received}")
    print(f"URL:       {url}")
    print("─" * 60)
    if result.content:
        print(result.content[:800])
    else:
        print("(no content returned)")
    print("─" * 60)

    if not result.success and result.error_message:
        print(f"\nError: {result.error_message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/crawl.py <URL>", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
