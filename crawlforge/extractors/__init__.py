"""Extractors package — Protocol + strategy implementations."""

from crawlforge.extractors.base import Extractor
from crawlforge.extractors.css import CssExtractor
from crawlforge.extractors.deepcrawl import DeepCrawlExtractor
from crawlforge.extractors.fullpage import FullPageExtractor
from crawlforge.extractors.html import HtmlExtractor

__all__ = [
    "Extractor",
    "CssExtractor",
    "DeepCrawlExtractor",
    "FullPageExtractor",
    "HtmlExtractor",
]
