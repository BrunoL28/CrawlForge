import asyncio
import sys
from pathlib import Path
from loguru import logger

from crawlforge.config.settings import get_settings
from crawlforge.core.engine import CrawlerEngine
from crawlforge.core.session import SessionHandler
from crawlforge.queue.manager import QueueManager
from crawlforge.exporters.markdown import MarkdownExporter
from crawlforge.models.schemas import CrawlJob
from crawlforge.models.enums import OutputFormat

async def main():
    # 1. Setup
    settings = get_settings()
    settings.queue_num_workers = 3
    
    # Configure logger to be concise
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Initialize components
    await SessionHandler.global_start(settings)
    engine = CrawlerEngine(settings)
    exporter = MarkdownExporter()

    # Define processor for QueueManager
    async def process_job(job: CrawlJob):
        logger.info(f"Processing job {job.id} for {job.url}")
        result = await engine.execute(job)
        if result.success:
            output_path = await exporter.export(result.content, job)
            logger.info(f"Exported to {output_path}")
        else:
            logger.error(f"Job {job.id} failed: {result.error_message}")

    queue_manager = QueueManager(settings, process_job)

    # 2. Add 10 URLs to the queue
    urls = [
        "https://example.com",
        "https://httpbin.org/get",
        "https://www.google.com",
        "https://www.wikipedia.org",
        "https://www.python.org",
        "https://www.github.com",
        "https://www.reddit.com",
        "https://www.stackoverflow.com",
        "https://www.amazon.com",
        "https://www.apple.com"
    ]

    logger.info(f"Adding {len(urls)} URLs to queue...")
    # Using a subset if some fail or to be faster for demo
    # But user asked for 10
    config_template = {
        "output_format": OutputFormat.MARKDOWN,
        "use_magic": True
    }
    
    await queue_manager.add_batch(urls, config_template)

    # 3. Start workers and process
    logger.info("Starting processing with 3 workers...")
    await queue_manager.start()

    # Wait for queue to be empty
    while True:
        await asyncio.sleep(2)
        # Simplified check: if all jobs in _jobs are either COMPLETED or FAILED
        all_done = all(
            j.status in ["completed", "failed", "cancelled"] 
            for j in queue_manager._jobs.values()
        )
        if all_done:
            break
        logger.info(f"Progress: {len([j for j in queue_manager._jobs.values() if j.status == 'completed'])}/10 done")

    await queue_manager.stop()
    logger.info("Demo complete!")

if __name__ == "__main__":
    asyncio.run(main())
