from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Any
from loguru import logger
from crawl4ai import AsyncWebCrawler

if TYPE_CHECKING:
    from crawlforge.config.settings import Settings
    from crawlforge.core.context import ContextHandler


@dataclass
class BrowserSession:
    """Represents a reusable crawler session."""
    id: str
    domain: str
    created_at: float
    cookies: List[dict] = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)
    crawler: Optional[AsyncWebCrawler] = None

    def is_expired(self, ttl: int) -> bool:
        return (time.monotonic() - self.last_used) > ttl


class SessionHandler:
    """
    Orchestrator for browser sessions. 
    Can be used as an async context manager for CrawlerEngine compatibility.
    Manages a pool of reusable sessions partitioned by domain.
    """

    _pool: Dict[str, List[BrowserSession]] = {}
    _cleanup_task: Optional[asyncio.Task] = None
    _started = False

    def __init__(
        self, 
        context: ContextHandler, 
        session_id: Optional[str] = None
    ) -> None:
        self.context = context
        self.session_id = session_id
        self.current_session: Optional[BrowserSession] = None
        self.domain = "default" # Will be updated if possible

    @classmethod
    async def global_start(cls, settings: Settings) -> None:
        if cls._started:
            return
        cls._started = True
        cls.settings = settings
        cls._cleanup_task = asyncio.create_task(cls._cleanup_loop())
        logger.info("SessionPool started with TTL={}s", settings.session_ttl_seconds)

    async def __aenter__(self) -> SessionHandler:
        # Determine domain (simple heuristic or from context)
        # Note: In CrawlerEngine, ctx doesn't have domain yet.
        # We might need to fetch the session when crawl() is called, 
        # but the interface expects it in __aenter__.
        
        domain = self.domain
        pool = self._pool.setdefault(domain, [])

        # Try to reuse
        found = None
        if self.session_id:
            for s in pool:
                if s.id == self.session_id:
                    found = s
                    break
        
        if not found and pool:
            s = pool.pop(0)
            if not s.is_expired(self.settings.session_ttl_seconds):
                found = s
            else:
                if s.crawler:
                    await s.crawler.close()
                logger.debug("Session {} expired", s.id)

        if found:
            self.current_session = found
            self.current_session.last_used = time.monotonic()
            logger.debug("Reusing session {}", found.id)
        else:
            import uuid
            new_id = self.session_id or uuid.uuid4().hex[:12]
            self.current_session = BrowserSession(
                id=new_id,
                domain=domain,
                created_at=time.monotonic()
            )
            logger.info("Created new session {} for {}", new_id, domain)

        # Initialize crawler if not present
        if not self.current_session.crawler:
            self.current_session.crawler = AsyncWebCrawler(
                config=self.context.to_browser_config()
            )
            await self.current_session.crawler.start()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.current_session:
            self.current_session.last_used = time.monotonic()
            pool = self._pool.setdefault(self.domain, [])
            if self.current_session not in pool:
                pool.append(self.current_session)
            
            # Limit pool size
            if len(pool) > self.settings.session_pool_size:
                removed = pool.pop(0)
                if removed.crawler:
                    await removed.crawler.close()
                logger.debug("Evicted session {}", removed.id)

    async def crawl(self, url: str, **kwargs) -> Any:
        if not self.current_session or not self.current_session.crawler:
            raise RuntimeError("Session not initialized. Use 'async with SessionHandler(...)'")
        
        # Update domain if default
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if self.domain == "default" and domain:
             # Logic to move session between domain pools if needed
             pass

        return await self.current_session.crawler.arun(url, **kwargs)

    @classmethod
    async def _cleanup_loop(cls) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                ttl = cls.settings.session_ttl_seconds
                for domain, pool in cls._pool.items():
                    valid = []
                    for s in pool:
                        if not s.is_expired(ttl):
                            valid.append(s)
                        else:
                            if s.crawler:
                                await s.crawler.close()
                    cls._pool[domain] = valid
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in session cleanup loop")
