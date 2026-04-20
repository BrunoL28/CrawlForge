"""
crawlforge.core.context
~~~~~~~~~~~~~~~~~~~~~~~~
ContextHandler — groups browser-level configuration:
viewport, user-agent, cookies, headers, proxy.

Wraps crawl4ai's BrowserConfig for consistent API surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from crawl4ai import BrowserConfig

from crawlforge.config.settings import Settings


@dataclass
class ContextHandler:
    """
    Immutable browser-context descriptor.
    Built once per session and passed to SessionHandler.
    """

    browser_type: str = "chromium"
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    proxy_config: dict[str, str] | None = None
    text_mode: bool = False
    light_mode: bool = False
    extra_args: list[str] = field(default_factory=list)

    @classmethod
    def from_settings(cls, settings: Settings) -> ContextHandler:
        """Build a default context from application settings."""
        return cls(
            browser_type=settings.crawl4ai_browser_type,
            headless=settings.crawl4ai_headless,
            viewport_width=settings.crawl4ai_viewport_width,
            viewport_height=settings.crawl4ai_viewport_height,
            text_mode=settings.crawl4ai_text_mode,
            light_mode=settings.crawl4ai_light_mode,
        )

    def to_browser_config(self) -> BrowserConfig:
        """Convert to crawl4ai BrowserConfig for AsyncWebCrawler init."""
        kwargs: dict = {
            "browser_type": self.browser_type,
            "headless": self.headless,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "cookies": self.cookies,
            "headers": self.headers,
            "proxy_config": self.proxy_config,
            "text_mode": self.text_mode,
            "light_mode": self.light_mode,
            "extra_args": self.extra_args,
            "verbose": False,
        }
        # crawl4ai's BrowserConfig passes user_agent directly into re.search(),
        # which raises TypeError when the value is None.  Only set it when we
        # have an explicit string so that crawl4ai uses its own safe default.
        if self.user_agent:
            kwargs["user_agent"] = self.user_agent
        return BrowserConfig(**kwargs)

