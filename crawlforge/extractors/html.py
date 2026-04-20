"""
crawlforge.extractors.html
~~~~~~~~~~~~~~~~~~~~~~~~~~~
HTML extraction — returns cleaned HTML with optional script/style removal.
"""

from __future__ import annotations

import re
from typing import Any

from crawl4ai import CacheMode, CrawlerRunConfig

# Pre-compiled patterns for stripping script/style tags
_SCRIPT_RE = re.compile(r"<script\b[^>]*>[\s\S]*?</script>", re.IGNORECASE)
_STYLE_RE = re.compile(r"<style\b[^>]*>[\s\S]*?</style>", re.IGNORECASE)
_NOSCRIPT_RE = re.compile(r"<noscript\b[^>]*>[\s\S]*?</noscript>", re.IGNORECASE)


class HtmlExtractor:
    """
    Extracts the cleaned HTML from a page.

    Options:
        remove_scripts: Strip all ``<script>`` tags (default: True)
        remove_styles: Strip all ``<style>`` tags (default: True)
        remove_noscript: Strip ``<noscript>`` tags (default: True)
    """

    def __init__(
        self,
        *,
        remove_scripts: bool = True,
        remove_styles: bool = True,
        remove_noscript: bool = True,
    ) -> None:
        self._remove_scripts = remove_scripts
        self._remove_styles = remove_styles
        self._remove_noscript = remove_noscript

    @property
    def name(self) -> str:
        return "html"

    def build_config(self, **kwargs: Any) -> CrawlerRunConfig:
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=kwargs.get("word_count_threshold", 10),
        )

    def post_process(self, raw_content: str | None, **kwargs: Any) -> str:
        """
        Return cleaned HTML, optionally stripping script and style tags.

        Accepts ``crawl_result`` kwarg — if present, prefers
        ``cleaned_html`` over ``html``.
        """
        crawl_result = kwargs.get("crawl_result")
        html = raw_content or ""

        if crawl_result is not None:
            html = (
                getattr(crawl_result, "cleaned_html", None)
                or getattr(crawl_result, "html", None)
                or html
            )

        if self._remove_scripts:
            html = _SCRIPT_RE.sub("", html)
        if self._remove_styles:
            html = _STYLE_RE.sub("", html)
        if self._remove_noscript:
            html = _NOSCRIPT_RE.sub("", html)

        return html.strip()
