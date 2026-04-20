"""
crawlforge.middleware.proxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Proxy rotation middleware — StaticProxy, RotatingProxyList with health checks.
Integrates with crawl4ai's BrowserConfig via ContextHandler.proxy_config.
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from loguru import logger

from crawlforge.core.context import ContextHandler


class ProxyProvider(ABC):
    """
    Abstract interface for proxy providers.
    Implementations supply proxy configs and integrate with ContextHandler.
    """

    @abstractmethod
    def get_proxy(self) -> dict[str, str]:
        """
        Return a proxy configuration dict compatible with crawl4ai.

        Expected keys:
            - server: "http://host:port"
            - username: (optional)
            - password: (optional)
        """
        ...

    def apply(self, context: ContextHandler) -> ContextHandler:
        """Apply the next proxy to the context."""
        context.proxy_config = self.get_proxy()
        return context

    @abstractmethod
    async def health_check(self, test_url: str = "https://httpbin.org/ip") -> bool:
        """Check if the proxy is reachable."""
        ...


class StaticProxy(ProxyProvider):
    """
    Single fixed proxy — always returns the same proxy config.

    Args:
        server: Proxy server URL, e.g. "http://proxy.example.com:8080"
        username: Optional proxy auth username.
        password: Optional proxy auth password.
    """

    def __init__(
        self,
        server: str,
        *,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._proxy: dict[str, str] = {"server": server}
        if username:
            self._proxy["username"] = username
        if password:
            self._proxy["password"] = password

    def get_proxy(self) -> dict[str, str]:
        return self._proxy.copy()

    async def health_check(self, test_url: str = "https://httpbin.org/ip") -> bool:
        """Check if the static proxy is reachable."""
        proxy_url = self._proxy["server"]
        if self._proxy.get("username"):
            # Insert auth into URL for httpx
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(proxy_url)
            auth_netloc = f"{self._proxy['username']}:{self._proxy.get('password', '')}@{parsed.netloc}"
            proxy_url = urlunparse(parsed._replace(netloc=auth_netloc))

        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
                resp = await client.get(test_url)
                healthy = resp.status_code == 200
                logger.debug(
                    "Proxy health check: server={} status={} healthy={}",
                    self._proxy["server"], resp.status_code, healthy,
                )
                return healthy
        except Exception as exc:
            logger.warning("Proxy health check failed: server={} error={}", self._proxy["server"], exc)
            return False


@dataclass
class ProxyStatus:
    """Track health state of a proxy."""
    proxy: dict[str, str]
    alive: bool = True
    fail_count: int = 0
    last_checked: float = 0.0


class RotatingProxyList(ProxyProvider):
    """
    Rotates through a list of proxy servers, skipping unhealthy ones.

    Features:
    - Round-robin rotation with dead proxy skipping
    - Async health checks via HTTP HEAD to a test URL
    - Auto-mark proxies as dead after N consecutive failures
    - Periodic health check to revive dead proxies

    Args:
        proxies: List of proxy dicts, each with 'server' and optionally
                 'username' and 'password' keys.
        max_failures: Consecutive failures before marking proxy as dead.
    """

    def __init__(
        self,
        proxies: list[dict[str, str]],
        *,
        max_failures: int = 3,
    ) -> None:
        if not proxies:
            raise ValueError("At least one proxy must be provided")

        self._statuses: list[ProxyStatus] = [
            ProxyStatus(proxy=p) for p in proxies
        ]
        self._index = 0
        self._max_failures = max_failures

    def get_proxy(self) -> dict[str, str]:
        """
        Get the next alive proxy in round-robin order.
        If all proxies are dead, resets all to alive and returns the first one.
        """
        alive = [s for s in self._statuses if s.alive]
        if not alive:
            logger.warning("All proxies dead — resetting all to alive")
            for s in self._statuses:
                s.alive = True
                s.fail_count = 0
            alive = self._statuses

        idx = self._index % len(alive)
        self._index += 1
        selected = alive[idx]
        logger.debug("Proxy selected: {}", selected.proxy.get("server", "?"))
        return selected.proxy.copy()

    def mark_failed(self, server: str) -> None:
        """Mark a proxy as failed. After max_failures, mark as dead."""
        for status in self._statuses:
            if status.proxy.get("server") == server:
                status.fail_count += 1
                if status.fail_count >= self._max_failures:
                    status.alive = False
                    logger.warning("Proxy marked dead: {} (failures={})", server, status.fail_count)
                break

    def mark_success(self, server: str) -> None:
        """Reset failure count for a proxy that succeeded."""
        for status in self._statuses:
            if status.proxy.get("server") == server:
                status.fail_count = 0
                status.alive = True
                break

    async def health_check(self, test_url: str = "https://httpbin.org/ip") -> bool:
        """Run health checks on all proxies concurrently."""
        tasks = []
        for status in self._statuses:
            tasks.append(self._check_single(status, test_url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        alive_count = sum(1 for s in self._statuses if s.alive)
        total = len(self._statuses)
        logger.info("Proxy health check: {}/{} alive", alive_count, total)
        return alive_count > 0

    async def _check_single(self, status: ProxyStatus, test_url: str) -> None:
        """Check health of a single proxy."""
        proxy_url = status.proxy["server"]
        if status.proxy.get("username"):
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(proxy_url)
            auth_netloc = f"{status.proxy['username']}:{status.proxy.get('password', '')}@{parsed.netloc}"
            proxy_url = urlunparse(parsed._replace(netloc=auth_netloc))

        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0) as client:
                resp = await client.get(test_url)
                if resp.status_code == 200:
                    status.alive = True
                    status.fail_count = 0
                else:
                    status.fail_count += 1
                    if status.fail_count >= self._max_failures:
                        status.alive = False
        except Exception:
            status.fail_count += 1
            if status.fail_count >= self._max_failures:
                status.alive = False
