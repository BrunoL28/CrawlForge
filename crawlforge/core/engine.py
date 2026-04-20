"""
crawlforge.core.engine
~~~~~~~~~~~~~~~~~~~~~~~
CrawlerEngine — high-level orchestrator.
Combines ContextHandler + SessionHandler + Extractors + Middleware
to execute CrawlJob instances end-to-end.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from crawl4ai import CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from loguru import logger

from crawlforge.core.context import ContextHandler
from crawlforge.core.session import SessionHandler
from crawlforge.extractors.css import CssExtractor
from crawlforge.extractors.deepcrawl import DeepCrawlExtractor
from crawlforge.extractors.fullpage import FullPageExtractor
from crawlforge.extractors.html import HtmlExtractor
from crawlforge.logger.setup import log_job_metrics
from crawlforge.middleware.antibot import AntiBotMiddleware, StealthMiddleware
from crawlforge.middleware.proxy import ProxyProvider, RotatingProxyList, StaticProxy
from crawlforge.models.enums import ExtractionStrategy, OutputFormat, ScrollMode
from crawlforge.models.schemas import CrawlJob, CrawlResultData

if TYPE_CHECKING:
    from crawlforge.config.settings import Settings


class CrawlerEngine:
    """
    Top-level engine that turns a CrawlJob into a CrawlResultData.

    Responsibilities:
    - Build ContextHandler from settings
    - Apply anti-bot and proxy middleware to context
    - Dispatch to the appropriate Extractor based on job.strategy
    - Configure scrolling (infinite / to-selector)
    - Apply wait_for conditions
    - Manage sessions via SessionHandler for context reuse
    - Execute the crawl and map results
    """

    def __init__(
        self,
        settings: Settings,
        *,
        antibot: AntiBotMiddleware | None = None,
        proxy_providers: dict[str, ProxyProvider] | None = None,
    ) -> None:
        self._settings = settings
        self._default_context = ContextHandler.from_settings(settings)
        self._antibot = antibot
        self._proxy_providers = proxy_providers or {}

    # ── Extractor factory ────────────────────────────
    def _get_extractor(self, job: CrawlJob) -> FullPageExtractor | CssExtractor | HtmlExtractor | None:
        """Return the appropriate extractor for the job's strategy."""
        if job.strategy == ExtractionStrategy.FULL:
            return FullPageExtractor(use_fit_markdown=True)

        if job.strategy == ExtractionStrategy.CSS and job.selectors is not None:
            schema_dict = {
                "name": job.selectors.name,
                "baseSelector": job.selectors.base_selector,
                "fields": [f.model_dump(exclude_none=True) for f in job.selectors.fields],
            }
            return CssExtractor(schema=schema_dict)

        if job.strategy == ExtractionStrategy.HTML:
            return HtmlExtractor(
                remove_scripts=job.remove_scripts,
                remove_styles=job.remove_styles,
            )

        # DEEP_CRAWL is handled separately in execute()
        return None

    # ── CrawlerRunConfig builder ─────────────────────
    def _build_run_config(
        self,
        job: CrawlJob,
        extractor: Any | None = None,
        antibot_overrides: dict[str, Any] | None = None,
    ) -> CrawlerRunConfig:
        """
        Translate a CrawlJob into a crawl4ai CrawlerRunConfig.

        Merges:
        1. Extractor's base config
        2. Scrolling parameters
        3. Wait-for conditions
        4. Anti-bot overrides (magic, simulate_user, etc.)
        """
        config_kwargs: dict[str, Any] = {
            "cache_mode": CacheMode.BYPASS,
            "word_count_threshold": 10,
            "verbose": self._settings.crawl4ai_verbose,
        }

        # ── Extraction strategy ──────────────────────
        if isinstance(extractor, CssExtractor):
            config_kwargs["extraction_strategy"] = extractor._strategy

        # ── Scrolling ────────────────────────────────
        if job.scroll_mode == ScrollMode.FULL:
            config_kwargs["scan_full_page"] = True
            config_kwargs["scroll_delay"] = job.scroll_delay

        elif job.scroll_mode == ScrollMode.SELECTOR and job.scroll_selector:
            # Inject JS to scroll until selector is visible
            js_scroll = f"""
            (async () => {{
                const maxScrolls = 50;
                for (let i = 0; i < maxScrolls; i++) {{
                    const target = document.querySelector('{job.scroll_selector}');
                    if (target) break;
                    window.scrollBy(0, window.innerHeight);
                    await new Promise(r => setTimeout(r, {int(job.scroll_delay * 1000)}));
                }}
            }})();
            """
            config_kwargs["js_code"] = [js_scroll]

        # ── Wait conditions ──────────────────────────
        if job.wait_for:
            config_kwargs["wait_for"] = job.wait_for
            config_kwargs["wait_for_timeout"] = job.wait_for_timeout

        # ── Session reuse ────────────────────────────
        config_kwargs["session_id"] = job.session_id

        # ── Anti-bot overrides ───────────────────────
        if antibot_overrides:
            config_kwargs.update(antibot_overrides)

        # ── Magic mode ───────────────────────────────
        if job.use_magic:
            config_kwargs["magic"] = True
            config_kwargs["simulate_user"] = True
            config_kwargs["override_navigator"] = True
            config_kwargs["remove_overlay_elements"] = True

        return CrawlerRunConfig(**config_kwargs)

    # ── Apply middleware ─────────────────────────────
    def _apply_middleware(self, job: CrawlJob, context: ContextHandler) -> tuple[ContextHandler, dict[str, Any]]:
        """
        Apply anti-bot and proxy middleware to the context.

        Returns:
            Tuple of (modified context, CrawlerRunConfig overrides).
        """
        antibot_overrides: dict[str, Any] = {}

        # Anti-bot middleware
        if job.use_antibot and self._antibot is not None:
            context, antibot_overrides = self._antibot.apply(context)

        # Proxy middleware
        if job.proxy_provider and job.proxy_provider in self._proxy_providers:
            provider = self._proxy_providers[job.proxy_provider]
            context = provider.apply(context)

        return context, antibot_overrides

    # ── Main execute ─────────────────────────────────
    async def execute(
        self,
        job: CrawlJob,
        *,
        context: ContextHandler | None = None,
    ) -> CrawlResultData:
        """
        Execute a single crawl job end-to-end.

        Args:
            job: The CrawlJob to execute.
            context: Optional ContextHandler override (defaults to settings-derived).

        Returns:
            CrawlResultData with all extracted content and metrics.
        """
        ctx = context or ContextHandler.from_settings(self._settings)
        start = time.monotonic()

        # Apply middleware pipeline
        ctx, antibot_overrides = self._apply_middleware(job, ctx)

        # ── Deep crawl special path ──────────────────
        if job.strategy == ExtractionStrategy.DEEP_CRAWL:
            return await self._execute_deep_crawl(job, ctx, start)

        # ── Standard crawl ───────────────────────────
        extractor = self._get_extractor(job)
        run_config = self._build_run_config(job, extractor, antibot_overrides)

        try:
            async with SessionHandler(ctx, session_id=job.session_id) as session:
                crawl_result = await session.crawl(str(job.url), config=run_config)
        except Exception as exc:
            return self._error_result(job, start, exc)

        duration_ms = (time.monotonic() - start) * 1000

        # ── Map content based on output format ───────
        content = ""
        raw_markdown: str | None = None

        if crawl_result.markdown:
            raw_markdown = (
                crawl_result.markdown.raw_markdown
                if hasattr(crawl_result.markdown, "raw_markdown")
                else str(crawl_result.markdown)
            )

        # Use extractor's post_process if available
        if extractor is not None:
            if job.output_format == OutputFormat.MARKDOWN:
                content = extractor.post_process(
                    raw_markdown, crawl_result=crawl_result,
                )
            elif job.output_format == OutputFormat.HTML:
                content = extractor.post_process(
                    crawl_result.cleaned_html or crawl_result.html or "",
                    crawl_result=crawl_result,
                )
            else:
                content = extractor.post_process(
                    raw_markdown, crawl_result=crawl_result,
                )
        else:
            if job.output_format == OutputFormat.MARKDOWN:
                content = raw_markdown or ""
            elif job.output_format == OutputFormat.HTML:
                content = crawl_result.cleaned_html or crawl_result.html or ""
            else:
                content = raw_markdown or ""

        bytes_received = len(content.encode("utf-8", errors="replace"))

        # ── Structured extraction result ─────────────
        extracted = crawl_result.extracted_content if crawl_result.extracted_content else None

        result = CrawlResultData(
            job_id=job.id,
            url=str(job.url),
            success=crawl_result.success,
            status_code=crawl_result.status_code,
            content=content,
            content_format=job.output_format,
            raw_markdown=raw_markdown,
            extracted_content=extracted,
            metadata=crawl_result.metadata or {},
            links=crawl_result.links or {},
            media=crawl_result.media or {},
            duration_ms=duration_ms,
            bytes_received=bytes_received,
            error_message=crawl_result.error_message,
        )

        log_job_metrics(
            session_id=job.session_id,
            url=str(job.url),
            duration_ms=duration_ms,
            bytes_received=bytes_received,
            status="ok" if crawl_result.success else "failed",
            error=crawl_result.error_message,
        )

        return result

    # ── Deep crawl path ──────────────────────────────
    async def _execute_deep_crawl(
        self,
        job: CrawlJob,
        ctx: ContextHandler,
        start: float,
        overrides: dict[str, Any] | None = None,
    ) -> CrawlResultData:
        """Execute a deep crawl and wrap result as CrawlResultData."""
        import json

        extractor = DeepCrawlExtractor(
            max_depth=job.depth,
            max_pages=50,
            respect_robots=True,
            delay_between_pages=0.5,
            user_agent=self._settings.robot_user_agent,
        )

        def session_factory():
            return SessionHandler(ctx, session_id=job.session_id)

        try:
            # Pass overrides to the deep crawl execution
            deep_result = await extractor.execute(
                root_url=str(job.url),
                session_handler_factory=session_factory,
                config_overrides=overrides,
            )
        except Exception as exc:
            return self._error_result(job, start, exc)

        duration_ms = (time.monotonic() - start) * 1000

        # Serialize deep crawl result as JSON content
        content = json.dumps(deep_result.model_dump(), indent=2, ensure_ascii=False, default=str)

        log_job_metrics(
            session_id=job.session_id,
            url=str(job.url),
            duration_ms=duration_ms,
            bytes_received=len(content.encode()),
            status="ok",
        )

        return CrawlResultData(
            job_id=job.id,
            url=str(job.url),
            success=True,
            content=content,
            content_format=job.output_format,
            duration_ms=duration_ms,
            bytes_received=len(content.encode()),
        )

    # ── Error helper ─────────────────────────────────
    def _error_result(self, job: CrawlJob, start: float, exc: Exception) -> CrawlResultData:
        """Build an error CrawlResultData from an exception."""
        duration_ms = (time.monotonic() - start) * 1000
        logger.exception(
            "Engine error — job={} url={} error={}",
            job.id, str(job.url), str(exc),
        )
        log_job_metrics(
            session_id=job.session_id,
            url=str(job.url),
            duration_ms=duration_ms,
            bytes_received=0,
            status="error",
            error=str(exc),
        )
        return CrawlResultData(
            job_id=job.id,
            url=str(job.url),
            success=False,
            error_message=str(exc),
            duration_ms=duration_ms,
        )
