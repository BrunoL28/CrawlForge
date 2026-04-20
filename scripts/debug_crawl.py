"""Diagnostic script to trace the exact source of the NoneType error."""
import asyncio
import traceback

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig


async def main():
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url="https://dronline.ie/",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
            )
        print(f"success: {result.success}")
        print(f"error_message: {result.error_message!r}")
        print(f"html length: {len(result.html or '')}")
        print(f"markdown type: {type(result.markdown)}")
    except Exception:
        print("=== FULL TRACEBACK ===")
        traceback.print_exc()
        print("=====================")


asyncio.run(main())
