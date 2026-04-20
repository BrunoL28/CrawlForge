"""
crawlforge.middleware.antibot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Anti-bot middleware — user-agent randomisation, random delays,
stealth browser flags, and crawl4ai magic mode support.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from crawlforge.core.context import ContextHandler

try:
    from fake_useragent import UserAgent as FakeUA
    _FAKE_UA = FakeUA(browsers=["chrome", "firefox", "edge"], os=["windows", "macos", "linux"])
except ImportError:
    _FAKE_UA = None


# Fallback user agents when fake_useragent is not installed
_FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]


class AntiBotMiddleware(ABC):
    """
    Abstract interface for anti-bot evasion middleware.
    Implementations modify the ContextHandler and return config overrides.
    """

    @abstractmethod
    def apply(self, context: ContextHandler) -> tuple[ContextHandler, dict[str, Any]]:
        """
        Modify the context handler with anti-detection settings.

        Args:
            context: The current ContextHandler.

        Returns:
            Tuple of (modified ContextHandler, CrawlerRunConfig overrides dict).
        """
        ...


@dataclass
class StealthConfig:
    """Configuration for the StealthMiddleware."""
    delay_min_ms: int = 500       # minimum delay before extracting (ms)
    delay_max_ms: int = 3000      # maximum delay
    use_magic: bool = True        # enable crawl4ai magic mode
    simulate_user: bool = True    # simulate human behaviour
    override_navigator: bool = True  # mask navigator properties
    remove_overlays: bool = True  # auto-remove popups/cookie banners
    stealth_args: list[str] = field(default_factory=lambda: [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
    ])


class StealthMiddleware(AntiBotMiddleware):
    """
    Production-grade anti-bot middleware.

    Features:
    - Random user-agent via ``fake_useragent`` (falls back to static list)
    - Random delay between requests (configurable min/max ms)
    - Magic mode: auto-handle popups, cookie banners, overlay elements
    - Simulate human behavior: mouse movements, random timings
    - Override navigator properties to hide automation signals
    - Stealth Chrome args to disable automation detection
    """

    def __init__(self, config: StealthConfig | None = None) -> None:
        self._config = config or StealthConfig()

    def _random_user_agent(self) -> str:
        """Get a random user-agent string."""
        if _FAKE_UA is not None:
            try:
                return _FAKE_UA.random
            except Exception:
                pass
        return random.choice(_FALLBACK_USER_AGENTS)

    def _random_delay(self) -> float:
        """Return a random delay in seconds between min and max."""
        delay_ms = random.randint(self._config.delay_min_ms, self._config.delay_max_ms)
        return delay_ms / 1000.0

    def apply(self, context: ContextHandler) -> tuple[ContextHandler, dict[str, Any]]:
        """
        Apply stealth configuration to context and return config overrides.

        Modifies:
        - context.user_agent → random UA
        - context.headers → realistic browser headers
        - context.extra_args → stealth Chrome flags

        Returns:
            CrawlerRunConfig overrides dict with magic, simulate_user, etc.
        """
        # ── User agent ───────────────────────────────
        ua = self._random_user_agent()
        context.user_agent = ua
        logger.debug("AntiBot: user_agent={}", ua[:60])

        # ── Realistic headers ────────────────────────
        context.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

        # ── Stealth browser args ─────────────────────
        for arg in self._config.stealth_args:
            if arg not in context.extra_args:
                context.extra_args.append(arg)

        # ── CrawlerRunConfig overrides ───────────────
        overrides: dict[str, Any] = {}

        if self._config.use_magic:
            overrides["magic"] = True

        if self._config.simulate_user:
            overrides["simulate_user"] = True

        if self._config.override_navigator:
            overrides["override_navigator"] = True

        if self._config.remove_overlays:
            overrides["remove_overlay_elements"] = True
            overrides["remove_consent_popups"] = True

        # Random delay before HTML capture
        delay = self._random_delay()
        overrides["delay_before_return_html"] = delay
        logger.debug("AntiBot: delay={:.2f}s", delay)

        return context, overrides
