"""
crawlforge.extractors.deepcrawl
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deep crawl extractor — BFS link discovery from a root URL up to depth N.
Respects robots.txt and returns a URL map + per-page content.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from crawl4ai import CacheMode, CrawlerRunConfig
from loguru import logger

from crawlforge.models.schemas import DeepCrawlPage, DeepCrawlResult


class DeepCrawlExtractor:
    """
    BFS crawler that discovers and extracts content from all internal links
    starting from a root URL, up to a configurable depth.

    Features:
    - BFS traversal of internal links only (same domain)
    - Respects robots.txt
    - Configurable max depth (0-5)
    - Returns adjacency map + per-page content
    """

    def __init__(
        self,
        *,
        max_depth: int = 2,
        max_pages: int = 50,
        respect_robots: bool = True,
        delay_between_pages: float = 0.5,
        user_agent: str = "CrawlForge",
    ) -> None:
        self._max_depth = min(max_depth, 5)
        self._max_pages = max_pages
        self._respect_robots = respect_robots
        self._delay = delay_between_pages
        self._user_agent = user_agent
        self._robot_parser: RobotFileParser | None = None

    @property
    def name(self) -> str:
        return "deep_crawl"

    def build_config(self, **kwargs: Any) -> CrawlerRunConfig:
        """Build config for individual page crawls within the BFS."""
        # Default settings
        config_args = {
            "cache_mode": CacheMode.BYPASS,
            "word_count_threshold": kwargs.pop("word_count_threshold", 0),
        }
        # Add any other overrides (magic, simulate_user, etc.)
        config_args.update(kwargs)
        return CrawlerRunConfig(**config_args)

    def post_process(self, raw_content: str | None, **kwargs: Any) -> str:
        """Not used directly — deep crawl uses execute() instead."""
        return raw_content or ""

    async def _load_robots(self, root_url: str) -> None:
        """Fetch and parse robots.txt for the root domain."""
        if not self._respect_robots:
            return

        parsed = urlparse(root_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        self._robot_parser = RobotFileParser()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    self._robot_parser.parse(resp.text.splitlines())
                    logger.debug("Loaded robots.txt from {}", robots_url)
                else:
                    self._robot_parser = None
                    logger.debug("No robots.txt at {} (status={})", robots_url, resp.status_code)
        except Exception as exc:
            self._robot_parser = None
            logger.debug("Failed to fetch robots.txt: {}", exc)

    def _is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if self._robot_parser is None:
            return True
        return self._robot_parser.can_fetch(self._user_agent, url)

    def _is_internal(self, url: str, root_domain: str) -> bool:
        """Check if URL belongs to the same domain as root."""
        parsed = urlparse(url)
        return parsed.netloc == root_domain or parsed.netloc == ""

    def _normalize_url(self, url: str, base_url: str) -> str | None:
        """Resolve relative URLs and filter out non-HTTP(S) schemes."""
        resolved = urljoin(base_url, url)
        parsed = urlparse(resolved)

        # Only http/https
        if parsed.scheme not in ("http", "https"):
            return None

        # Strip fragments
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean += f"?{parsed.query}"

        return clean

    async def execute(
        self,
        root_url: str,
        session_handler_factory: Any,  # Callable that returns async context manager
        *,
        config_overrides: dict[str, Any] | None = None,
    ) -> DeepCrawlResult:
        """
        Execute BFS crawl from root_url.

        Args:
            root_url: Starting URL for the crawl.
            session_handler_factory: Callable that creates a SessionHandler context manager.

        Returns:
            DeepCrawlResult with URL map and page content.
        """
        start = time.monotonic()
        root_domain = urlparse(root_url).netloc

        await self._load_robots(root_url)

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_url, 0)])
        pages: list[DeepCrawlPage] = []
        url_map: dict[str, list[str]] = {}
        # Build config with optional overrides
        config_kwargs = {}
        if config_overrides:
            config_kwargs.update(config_overrides)
        config = self.build_config(**config_kwargs)

        async with session_handler_factory() as session:
            while queue and len(visited) < self._max_pages:
                current_url, depth = queue.popleft()

                if current_url in visited:
                    continue
                if depth > self._max_depth:
                    continue
                if not self._is_allowed(current_url):
                    logger.warning("Blocked by robots.txt: {}", current_url)
                    pages.append(DeepCrawlPage(
                        url=current_url,
                        depth=depth,
                        success=False,
                        error_message=f"Blocked by robots.txt (User-Agent: {self._user_agent})",
                    ))
                    continue

                visited.add(current_url)
                logger.info(
                    "DeepCrawl [{}/{}] depth={} url={}",
                    len(visited), self._max_pages, depth, current_url,
                )

                try:
                    result = await session.crawl(current_url, config=config)
                except Exception as exc:
                    pages.append(DeepCrawlPage(
                        url=current_url,
                        depth=depth,
                        success=False,
                        error_message=str(exc),
                    ))
                    continue

                # Extract content
                content = ""
                if result.markdown:
                    content = (
                        getattr(result.markdown, "raw_markdown", None)
                        or str(result.markdown)
                    )

                # Discover links
                child_urls: list[str] = []
                raw_links = result.links or {}
                for link_list in raw_links.values():
                    for link_info in link_list:
                        href = link_info.get("href", "")
                        normalized = self._normalize_url(href, current_url)
                        if normalized and self._is_internal(normalized, root_domain):
                            child_urls.append(normalized)
                            if normalized not in visited and depth + 1 <= self._max_depth:
                                queue.append((normalized, depth + 1))

                url_map[current_url] = list(set(child_urls))
                pages.append(DeepCrawlPage(
                    url=current_url,
                    depth=depth,
                    success=result.success,
                    content=content,
                    links_found=list(set(child_urls)),
                    error_message=result.error_message,
                ))

                # Polite delay between requests
                if self._delay > 0 and queue:
                    await asyncio.sleep(self._delay)

        duration_ms = (time.monotonic() - start) * 1000

        return DeepCrawlResult(
            root_url=root_url,
            max_depth=self._max_depth,
            total_pages=len(pages),
            pages=pages,
            url_map=url_map,
            duration_ms=duration_ms,
        )
