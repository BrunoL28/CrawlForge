"""
crawlforge.extractors.fullpage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Full-page extraction — returns the complete markdown representation.
Prefers ``fit_markdown`` from crawl4ai for cleaner LLM-friendly output.
"""

from __future__ import annotations

from typing import Any

from crawl4ai import CacheMode, CrawlerRunConfig


class FullPageExtractor:
    """
    Full-page extractor: grabs the entire page content as markdown.
    When available, uses crawl4ai's ``fit_markdown`` for cleaner output
    that strips navigation, footers, and boilerplate.
    """

    def __init__(self, *, use_fit_markdown: bool = True) -> None:
        self._use_fit_markdown = use_fit_markdown

    @property
    def name(self) -> str:
        return "full"

    def build_config(self, **kwargs: Any) -> CrawlerRunConfig:
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=kwargs.get("word_count_threshold", 0),
        )

    def post_process(self, raw_content: str | None, **kwargs: Any) -> str:
        """
        Extract markdown content, preferring fit_markdown when available.

        Accepts ``crawl_result`` kwarg to access the MarkdownGenerationResult.
        """
        crawl_result = kwargs.get("crawl_result")

        if self._use_fit_markdown and crawl_result is not None:
            md = getattr(crawl_result, "markdown", None)
            if md is not None:
                fit = getattr(md, "fit_markdown", None)
                if fit:
                    return fit

        # Fallback to raw markdown
        if crawl_result is not None:
            md = getattr(crawl_result, "markdown", None)
            if md is not None:
                raw = getattr(md, "raw_markdown", None)
                if raw:
                    return raw

        return raw_content or ""
