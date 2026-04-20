import asyncio
import json
import os
from crawlforge.config.settings import Settings
from crawlforge.core.engine import CrawlerEngine
from crawlforge.models.schemas import CrawlJob
from crawlforge.models.enums import ExtractionStrategy, OutputFormat

from crawlforge.middleware.antibot import StealthMiddleware

async def main():
    print("\n--- Deep Crawl Test: dronline.pt ---")
    settings = Settings()
    
    # Initialize engine with StealthMiddleware
    engine = CrawlerEngine(settings, antibot=StealthMiddleware())
    
    # Create a Deep Crawl job with anti-bot features
    job = CrawlJob(
        url="https://dronline.pt/",
        strategy=ExtractionStrategy.DEEP_CRAWL,
        depth=1,
        output_format=OutputFormat.MARKDOWN,
        use_antibot=True,
        use_magic=True
    )
    
    print(f"Starting deep crawl at {job.url} (depth={job.depth})...")
    result = await engine.execute(job)
    
    if result.success:
        data = json.loads(result.content)
        total = data['total_pages']
        print(f"\nCrawl complete! Total pages: {total}")
        
        # Create an output directory
        out_dir = "data/dronline_crawl"
        os.makedirs(out_dir, exist_ok=True)
        
        # Save adjacency map
        with open(f"{out_dir}/discovery_map.json", "w", encoding="utf-8") as f:
            json.dump(data['url_map'], f, indent=2)
        
        # Save individual page contents
        for i, page in enumerate(data['pages']):
            safe_name = page['url'].replace("https://", "").replace("/", "_").strip("_")
            with open(f"{out_dir}/page_{i}_{safe_name}.md", "w", encoding="utf-8") as f:
                f.write(f"# URL: {page['url']}\n")
                f.write(f"## Depth: {page['depth']}\n\n")
                f.write(page['content'])
        
        print(f"Results saved to directory: {out_dir}")
        print("\nDiscovery Sample (1st 5 pages):")
        for url, links in list(data['url_map'].items())[:5]:
            print(f"- {url} -> {len(links)} internal links found")
            
    else:
        print(f"Engine failure: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
