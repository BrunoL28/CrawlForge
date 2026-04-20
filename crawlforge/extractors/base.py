"""
crawlforge.extractors.base
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Protocol interface for all extraction strategies.
Implement this to add new extraction backends.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from crawl4ai import CrawlerRunConfig


@runtime_checkable
class Extractor(Protocol):
    """
    Interface contract for content extractors.

    Each extractor knows how to:
    1. Build a crawl4ai CrawlerRunConfig with the right extraction_strategy
    2. Post-process the raw CrawlResult into structured data
    """

    @property
    def name(self) -> str:
        """Human-readable name for this extractor."""
        ...

    def build_config(self, **kwargs: Any) -> CrawlerRunConfig:
        """
        Build a CrawlerRunConfig tailored to this extraction strategy.

        Returns:
            Configured CrawlerRunConfig ready for AsyncWebCrawler.arun().
        """
        ...

    def post_process(self, raw_content: str | None, **kwargs: Any) -> str:
        """
        Transform raw extracted content into the final output.

        Args:
            raw_content: The raw content from CrawlResult.
            **kwargs: Extra context (e.g., crawl_result for markdown objects).

        Returns:
            Processed content string.
        """
        ...
