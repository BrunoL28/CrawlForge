"""
crawlforge.models.schemas
~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic v2 schemas for jobs, crawl requests/responses, and queue items.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from crawlforge.models.enums import (
    ExtractionStrategy,
    JobPriority,
    JobStatus,
    OutputFormat,
    ScrollMode,
)


# ── Selector config ──────────────────────────────────
class SelectorField(BaseModel):
    """Single field definition for CSS extraction."""
    name: str
    selector: str
    type: str = "text"  # text | attribute | html | regex
    attribute: str | None = None
    pattern: str | None = None
    default: str | None = None


class SelectorSchema(BaseModel):
    """Full CSS extraction schema matching crawl4ai's JsonCssExtractionStrategy format."""
    name: str = "default"
    base_selector: str = Field(..., alias="baseSelector")
    fields: list[SelectorField]

    model_config = {"populate_by_name": True}


# ── Crawl Job ────────────────────────────────────────
class CrawlJob(BaseModel):
    """
    A unit of work: crawl a single URL with specific extraction rules.
    Submitted to the queue and tracked through its lifecycle.
    """
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    url: HttpUrl
    strategy: ExtractionStrategy = ExtractionStrategy.FULL
    selectors: SelectorSchema | None = None
    output_format: OutputFormat = OutputFormat.MARKDOWN
    depth: int = Field(default=0, ge=0, le=5)
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    priority: int = Field(default=JobPriority.NORMAL, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)

    # ── Scrolling ────────────────────────────────────
    scroll_mode: ScrollMode = ScrollMode.NONE
    scroll_selector: str | None = None  # CSS selector for SELECTOR mode
    scroll_delay: float = 0.3  # seconds between scroll steps

    # ── Wait conditions ──────────────────────────────
    wait_for: str | None = None  # "css:.selector" or "js:() => expr"
    wait_for_timeout: int = 15000  # ms

    # ── Anti-bot ─────────────────────────────────────
    use_antibot: bool = False
    use_magic: bool = False  # crawl4ai magic mode

    # ── Proxy ────────────────────────────────────────
    proxy_provider: str | None = None  # "static" or "rotating"

    # ── HTML extraction options ──────────────────────
    remove_scripts: bool = True
    remove_styles: bool = True

    # ── Robots ───────────────────────────────────────
    respect_robots: bool = True

    # ── Lifecycle metadata (set by the system) ───────
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = {"use_enum_values": True}


# ── Crawl Result ─────────────────────────────────────
class CrawlResultData(BaseModel):
    """Structured output from a completed crawl job."""
    job_id: str
    url: str
    success: bool
    status_code: int | None = None
    content: str = ""
    content_format: OutputFormat = OutputFormat.MARKDOWN
    raw_markdown: str | None = None
    extracted_content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    media: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    duration_ms: float = 0.0
    bytes_received: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Deep Crawl Result ────────────────────────────────
class DeepCrawlPage(BaseModel):
    """Content extracted from a single page during deep crawl."""
    url: str
    depth: int
    success: bool
    content: str = ""
    links_found: list[str] = Field(default_factory=list)
    error_message: str | None = None


class DeepCrawlResult(BaseModel):
    """Result of a deep crawl — BFS traversal from root URL."""
    root_url: str
    max_depth: int
    total_pages: int = 0
    pages: list[DeepCrawlPage] = Field(default_factory=list)
    url_map: dict[str, list[str]] = Field(default_factory=dict)  # adjacency list
    duration_ms: float = 0.0


# ── API request/response ────────────────────────────
class CrawlRequest(BaseModel):
    """POST /api/v1/crawl request body."""
    url: HttpUrl
    strategy: ExtractionStrategy = ExtractionStrategy.FULL
    selectors: SelectorSchema | None = None
    output_format: OutputFormat = OutputFormat.MARKDOWN
    depth: int = Field(default=0, ge=0, le=5)
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)
    scroll_mode: ScrollMode = ScrollMode.NONE
    scroll_selector: str | None = None
    scroll_delay: float = 0.3
    wait_for: str | None = None
    wait_for_timeout: int = 15000
    use_antibot: bool = False
    use_magic: bool = False
    proxy_provider: str | None = None
    remove_scripts: bool = True
    remove_styles: bool = True
    respect_robots: bool = True


class CrawlResponse(BaseModel):
    """POST /api/v1/crawl response body."""
    job_id: str
    status: JobStatus
    message: str = "Job accepted"


class HealthResponse(BaseModel):
    """GET /health response body."""
    status: str = "ok"
    version: str
    environment: str
