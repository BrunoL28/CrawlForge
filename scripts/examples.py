import asyncio
import json
from crawlforge.config.settings import Settings
from crawlforge.core.engine import CrawlerEngine
from crawlforge.models.schemas import CrawlJob, SelectorSchema, SelectorField
from crawlforge.models.enums import ExtractionStrategy, OutputFormat, ScrollMode
from crawlforge.middleware.antibot import StealthMiddleware
from crawlforge.middleware.proxy import StaticProxy

async def example_full_page():
    print("\n--- Example: Full Page Extraction ---")
    settings = Settings()
    engine = CrawlerEngine(settings)
    
    job = CrawlJob(
        url="https://news.ycombinator.com",
        strategy=ExtractionStrategy.FULL,
        output_format=OutputFormat.MARKDOWN
    )
    
    result = await engine.execute(job)
    print(f"Success: {result.success}")
    if result.success:
        print(f"Content length: {len(result.content)}")
        print(f"Markdown preview:\n{result.content[:200]}...")

async def example_css_selectors():
    print("\n--- Example: CSS Structured Extraction ---")
    settings = Settings()
    engine = CrawlerEngine(settings)
    
    selectors = SelectorSchema(
        baseSelector="tr.athing",
        fields=[
            SelectorField(name="title", selector="td.title > span.titleline > a"),
            SelectorField(name="rank", selector="span.rank"),
            SelectorField(name="link", selector="td.title > span.titleline > a", type="attribute", attribute="href")
        ]
    )
    
    job = CrawlJob(
        url="https://news.ycombinator.com",
        strategy=ExtractionStrategy.CSS,
        selectors=selectors
    )
    
    result = await engine.execute(job)
    print(f"Success: {result.success}")
    if result.success:
        print(f"Extracted data:\n{result.content}")

async def example_html_clean():
    print("\n--- Example: Clean HTML Extraction ---")
    settings = Settings()
    engine = CrawlerEngine(settings)
    
    job = CrawlJob(
        url="https://news.ycombinator.com",
        strategy=ExtractionStrategy.HTML,
        remove_scripts=True,
        remove_styles=True
    )
    
    result = await engine.execute(job)
    print(f"Success: {result.success}")
    if result.success:
        print(f"HTML Preview:\n{result.content[:200]}...")

async def example_deep_crawl():
    print("\n--- Example: Deep Crawl (BFS) ---")
    settings = Settings()
    engine = CrawlerEngine(settings)
    
    job = CrawlJob(
        url="https://crawler-test.com/",  # A small site for testing
        strategy=ExtractionStrategy.DEEP_CRAWL,
        depth=1  # Only 1st level links
    )
    
    result = await engine.execute(job)
    print(f"Success: {result.success}")
    if result.success:
        data = json.loads(result.content)
        print(f"Total pages crawled: {data['total_pages']}")
        print(f"URLs mapped: {list(data['url_map'].keys())[:5]}")

async def example_antibot_proxy():
    print("\n--- Example: Anti-bot and Proxy ---")
    settings = Settings()
    
    # Optional: setup a proxy (this will likely fail without a real proxy, so we'll just show the config)
    # proxy_provider = StaticProxy(server="http://1.2.3.4:8080")
    # engine = CrawlerEngine(settings, antibot=StealthMiddleware(), proxy_providers={"static": proxy_provider})
    
    engine = CrawlerEngine(settings, antibot=StealthMiddleware())
    
    job = CrawlJob(
        url="https://httpbin.org/headers",
        use_antibot=True,
        use_magic=True
    )
    
    result = await engine.execute(job)
    print(f"Success: {result.success}")
    if result.success:
        print(f"Headers response:\n{result.content}")

async def main():
    await example_full_page()
    await example_css_selectors()
    await example_html_clean()
    await example_deep_crawl()
    await example_antibot_proxy()

if __name__ == "__main__":
    asyncio.run(main())
