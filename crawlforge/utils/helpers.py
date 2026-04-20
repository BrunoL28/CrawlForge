"""
crawlforge.utils.helpers
~~~~~~~~~~~~~~~~~~~~~~~~~
Shared utility functions used across the project.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """
    Normalize a URL by lowering the scheme/host and stripping trailing slashes.

    >>> normalize_url("HTTPS://Example.COM/path/")
    'https://example.com/path'
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = parsed.query
    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


def url_to_filename(url: str, max_length: int = 100) -> str:
    """
    Convert a URL into a safe filename.

    >>> url_to_filename("https://example.com/page/1")
    'example_com_page_1'
    """
    parsed = urlparse(url)
    name = f"{parsed.netloc}{parsed.path}"
    # Replace non-alphanumeric with underscores
    name = re.sub(r"[^a-zA-Z0-9]", "_", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:max_length]


def content_hash(content: str) -> str:
    """
    SHA-256 hash of content — useful for deduplication.

    >>> len(content_hash("hello"))
    64
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def truncate(text: str, max_chars: int = 500, suffix: str = "…") -> str:
    """Truncate text with ellipsis if it exceeds max_chars."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def bytes_to_human(size_bytes: int) -> str:
    """
    Convert bytes to human-readable string.

    >>> bytes_to_human(1536)
    '1.50 KB'
    """
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0  # type: ignore[assignment]
    return f"{size_bytes:.2f} TB"
