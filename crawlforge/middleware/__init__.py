"""Middleware package — Anti-bot, proxy rotation, captcha interfaces."""

from crawlforge.middleware.antibot import AntiBotMiddleware, StealthMiddleware
from crawlforge.middleware.proxy import ProxyProvider, RotatingProxyList, StaticProxy

__all__ = [
    "AntiBotMiddleware",
    "StealthMiddleware",
    "ProxyProvider",
    "RotatingProxyList",
    "StaticProxy",
]
