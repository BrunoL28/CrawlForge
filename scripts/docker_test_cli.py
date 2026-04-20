import asyncio
import argparse
import sys
from loguru import logger

from crawlforge.config.settings import get_settings
from crawlforge.core.engine import CrawlerEngine
from crawlforge.core.session import SessionHandler
from crawlforge.queue.manager import QueueManager
from crawlforge.exporters.markdown import MarkdownExporter
from crawlforge.models.schemas import CrawlJob
from crawlforge.models.enums import OutputFormat, ExtractionStrategy

async def main():
    parser = argparse.ArgumentParser(description="CrawlForge Docker Test CLI")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent workers")
    parser.add_argument("--urls", type=int, default=3, help="Number of test URLs to crawl (for multi-worker test)")
    parser.add_argument("--strategy", type=str, choices=["full", "deep"], default="full", help="Extraction strategy")
    parser.add_argument("--url", type=str, help="Specific URL for deep crawl")
    parser.add_argument("--ignore-robots", action="store_true", help="Ignore robots.txt rules")
    parser.add_argument("--format", type=str, choices=["markdown", "html", "text", "pdf"], default="markdown", help="Output format")
    
    args = parser.parse_args()

    settings = get_settings()
    settings.queue_num_workers = args.workers
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    await SessionHandler.global_start(settings)
    engine = CrawlerEngine(settings)
    
    # Select exporter
    from crawlforge.exporters.markdown import MarkdownExporter
    from crawlforge.exporters.html import HtmlExporter
    from crawlforge.exporters.text import TextExporter
    from crawlforge.exporters.pdf import PdfExporter

    exporters = {
        "markdown": MarkdownExporter(),
        "html": HtmlExporter(),
        "text": TextExporter(),
        "pdf": PdfExporter(),
    }
    exporter = exporters[args.format]

    # Map CLI format to OutputFormat enum values
    format_map = {
        "markdown": OutputFormat.MARKDOWN,
        "html": OutputFormat.HTML,
        "text": OutputFormat.TEXT,
        "pdf": OutputFormat.PDF
    }

    async def process_job(job: CrawlJob):
        logger.info(f"Worker processing job {job.id} for {job.url}")
        if args.ignore_robots:
            job.respect_robots = False
        
        job.output_format = format_map[args.format]
            
        result = await engine.execute(job)
        if result.success:
            if job.strategy == ExtractionStrategy.DEEP_CRAWL:
                import json
                from pathlib import Path
                # For deep crawl, we save the JSON summary AND individual pages
                # The 'content' returns a JSON string of the whole result
                summary_data = json.loads(result.content)
                
                # Save individual pages if markdown
                if args.format == "markdown":
                    base_path = Path("output") / f"deepcrawl_{job.id}"
                    base_path.mkdir(parents=True, exist_ok=True)
                    
                    for i, page in enumerate(summary_data.get("pages", [])):
                        # Create a safe filename
                        page_url = page.get("url", f"page_{i}")
                        safe_name = page_url.split("//")[-1].replace("/", "_")[:100] + ".md"
                        file_path = base_path / safe_name
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(page.get("content", ""))
                    logger.info(f"✅ DeepCrawl pages saved to {base_path}/")
                
                # Still save the summary JSON
                path = await exporter.export(result.content, job)
                logger.info(f"✅ Summary saved to {path}")
            else:
                path = await exporter.export(result.content, job)
                logger.info(f"✅ Success! Saved to {path}")
        else:
            logger.error(f"❌ Failed: {result.error_message}")

    queue_manager = QueueManager(settings, process_job)

    test_urls = [
        "https://example.com",
        "https://httpbin.org/get",
        "https://www.python.org",
        "https://www.reddit.com",
        "https://www.wikipedia.org"
    ]

    if args.strategy == "deep":
        if not args.url:
            logger.error("Deep crawl requires --url argument")
            return
        logger.info(f"Starting DEEP CRAWL on {args.url}...")
        job_config = {
            "strategy": ExtractionStrategy.DEEP_CRAWL,
            "output_format": OutputFormat.MARKDOWN,
            "depth": 1
        }
        await queue_manager.add_batch([args.url], job_config)
    else:
        urls_to_add = test_urls[:args.urls]
        logger.info(f"Starting MULTI-WORKER test ({args.workers} workers, {len(urls_to_add)} URLs)...")
        await queue_manager.add_batch(urls_to_add, {"output_format": OutputFormat.MARKDOWN})

    await queue_manager.start()

    # Simple wait
    while True:
        await asyncio.sleep(2)
        all_done = all(j.status in ["completed", "failed"] for j in queue_manager._jobs.values())
        if all_done: break

    await queue_manager.stop()
    logger.info("Test finished. Check the 'output/' directory.")

if __name__ == "__main__":
    asyncio.run(main())
