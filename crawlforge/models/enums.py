"""
crawlforge.models.enums
~~~~~~~~~~~~~~~~~~~~~~~~
All enumerations shared across the project.
"""

from __future__ import annotations

from enum import Enum


class ExtractionStrategy(str, Enum):
    """How to extract content from a crawled page."""
    CSS = "css"
    HTML = "html"
    FULL = "full"
    DEEP_CRAWL = "deep_crawl"


class ScrollMode(str, Enum):
    """How to handle page scrolling before extraction."""
    NONE = "none"
    FULL = "full"            # scroll entire page (scan_full_page)
    SELECTOR = "selector"    # scroll until a CSS selector appears


class OutputFormat(str, Enum):
    """Supported export formats for crawled content."""
    MARKDOWN = "md"
    HTML = "html"
    PDF = "pdf"
    TEXT = "txt"


class JobStatus(str, Enum):
    """Lifecycle states of a crawl job."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobPriority(int, Enum):
    """
    Numeric priority: lower number = higher priority.
    Provides named presets while allowing any int 1-10.
    """
    CRITICAL = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 10
