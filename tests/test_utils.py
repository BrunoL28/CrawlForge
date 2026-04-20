"""
tests.test_utils
~~~~~~~~~~~~~~~~~
Validate shared utility functions.
"""

from __future__ import annotations

from crawlforge.utils.helpers import (
    bytes_to_human,
    content_hash,
    normalize_url,
    truncate,
    url_to_filename,
)


class TestNormalizeUrl:
    def test_lowercases_scheme_and_host(self) -> None:
        assert normalize_url("HTTPS://Example.COM/path") == "https://example.com/path"

    def test_strips_trailing_slash(self) -> None:
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_preserves_query(self) -> None:
        result = normalize_url("https://example.com/search?q=test")
        assert "?q=test" in result


class TestUrlToFilename:
    def test_basic(self) -> None:
        result = url_to_filename("https://example.com/page/1")
        assert "example" in result
        assert "/" not in result

    def test_max_length(self) -> None:
        result = url_to_filename("https://example.com/" + "a" * 200, max_length=50)
        assert len(result) <= 50


class TestContentHash:
    def test_deterministic(self) -> None:
        assert content_hash("hello") == content_hash("hello")

    def test_different_inputs(self) -> None:
        assert content_hash("hello") != content_hash("world")

    def test_length(self) -> None:
        assert len(content_hash("test")) == 64


class TestTruncate:
    def test_short_text_unchanged(self) -> None:
        assert truncate("short", 100) == "short"

    def test_long_text_truncated(self) -> None:
        result = truncate("a" * 100, 50)
        assert len(result) == 50
        assert result.endswith("…")


class TestBytesToHuman:
    def test_bytes(self) -> None:
        assert bytes_to_human(500) == "500.00 B"

    def test_kilobytes(self) -> None:
        assert bytes_to_human(1536) == "1.50 KB"

    def test_megabytes(self) -> None:
        assert "MB" in bytes_to_human(2 * 1024 * 1024)
