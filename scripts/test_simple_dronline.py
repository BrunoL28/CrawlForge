import asyncio
from crawlforge.config.settings import Settings
from crawlforge.core.engine import CrawlerEngine
from crawlforge.models.schemas import CrawlJob
from crawlforge.models.enums import ExtractionStrategy, OutputFormat
from crawlforge.middleware.antibot import StealthMiddleware

async def main():
    print("\n--- Simple Crawl Test: dronline.pt ---")
    settings = Settings()
    
    # Use StealthMiddleware with some custom over-the-top settings if needed?
    # Actually let's just use the defaults first.
    # Add realistic browser signals
    engine = CrawlerEngine(settings, antibot=StealthMiddleware())
    job = CrawlJob(
        url="https://dronline.pt/",
        strategy=ExtractionStrategy.FULL,
        use_antibot=True,
        use_magic=True,
        wait_for_timeout=120000, # 2 minutes
    )
    
    print(f"Crawling {job.url}...")
    result = await engine.execute(job)
    
    print(f"Success: {result.success}")
    if not result.success:
        print(f"Error: {result.error_message}")
    else:
        print(f"Log length: {len(result.content)}")
    
if __name__ == "__main__":
    asyncio.run(main())
