"""
crawlforge.middleware.captcha
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Captcha handling middleware — interface for future integrations
(2captcha, hCaptcha solver, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from crawlforge.core.context import ContextHandler


class CaptchaMiddleware(ABC):
    """
    Abstract interface for CAPTCHA solving middleware.

    Implementations should integrate with a CAPTCHA solving service
    and modify the context or crawl config accordingly.
    """

    @abstractmethod
    async def solve(self, page_url: str, site_key: str) -> str:
        """
        Solve a CAPTCHA challenge.

        Args:
            page_url: The URL of the page with the CAPTCHA.
            site_key: The CAPTCHA site key.

        Returns:
            The CAPTCHA solution token.
        """
        ...

    @abstractmethod
    def apply(self, context: ContextHandler) -> ContextHandler:
        """Apply CAPTCHA-related settings to the context."""
        ...


class NoOpCaptchaMiddleware(CaptchaMiddleware):
    """Default no-op implementation — does nothing, lets crawl proceed."""

    async def solve(self, page_url: str, site_key: str) -> str:
        return ""

    def apply(self, context: ContextHandler) -> ContextHandler:
        return context
