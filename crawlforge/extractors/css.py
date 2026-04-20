"""
crawlforge.extractors.css
~~~~~~~~~~~~~~~~~~~~~~~~~~
CSS-selector based extraction using crawl4ai's JsonCssExtractionStrategy.
"""

from __future__ import annotations

import json
from typing import Any

from crawl4ai import CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy


class CssExtractor:
    """
    Extracts structured data via CSS selectors.

    Uses crawl4ai's JsonCssExtractionStrategy with a schema defining
    baseSelector and field mappings (name, selector, type).

    Each field in the schema has a ``name`` that acts as a label in the
    resulting JSON, making the output self-documenting.
    """

    def __init__(self, schema: dict[str, Any]) -> None:
        """
        Args:
            schema: Dict with keys:
                - ``name``: Schema name (default: "default")
                - ``baseSelector``: Root CSS selector for repeated items
                - ``fields``: List of dicts with:
                    - ``name``: Label for this field
                    - ``selector``: CSS selector relative to baseSelector
                    - ``type``: "text" | "attribute" | "html" | "regex"
                    - ``attribute``: Attribute name (when type="attribute")
                    - ``pattern``: Regex pattern (when type="regex")
        """
        self._schema = schema
        self._strategy = JsonCssExtractionStrategy(schema=schema)

    @property
    def name(self) -> str:
        return "css"

    def build_config(self, **kwargs: Any) -> CrawlerRunConfig:
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=self._strategy,
            word_count_threshold=kwargs.get("word_count_threshold", 10),
        )

    def post_process(self, raw_content: str | None, **kwargs: Any) -> str:
        """
        Parse extracted JSON and return labeled, indented output.

        Each item in the returned JSON array contains fields keyed by
        their ``name`` from the schema definition.
        """
        if not raw_content:
            return "[]"
        try:
            data = json.loads(raw_content)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return raw_content
