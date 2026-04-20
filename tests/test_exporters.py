"""
tests.test_exporters
~~~~~~~~~~~~~~~~~~~~~
Validate exporter Protocol implementations.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from crawlforge.exporters.base import Exporter
from crawlforge.exporters.markdown import MarkdownExporter
from crawlforge.exporters.html import HtmlExporter
from crawlforge.exporters.text import TextExporter
from crawlforge.models.enums import OutputFormat


class TestExporterProtocol:
    """All exporters should satisfy the Exporter Protocol."""

    def test_markdown_is_exporter(self) -> None:
        assert isinstance(MarkdownExporter(), Exporter)

    def test_html_is_exporter(self) -> None:
        assert isinstance(HtmlExporter(), Exporter)

    def test_text_is_exporter(self) -> None:
        assert isinstance(TextExporter(), Exporter)


class TestMarkdownExporter:
    """MarkdownExporter tests."""

    def test_format(self) -> None:
        assert MarkdownExporter().format == OutputFormat.MARKDOWN

    def test_export_without_metadata(self) -> None:
        content = "# Hello\nWorld"
        result = MarkdownExporter().export(content)
        assert result == content

    def test_export_with_metadata(self) -> None:
        result = MarkdownExporter().export("# Hello", {"title": "Test"})
        assert "---" in result
        assert "title: Test" in result

    @pytest.mark.asyncio
    async def test_save(self, tmp_path: Path) -> None:
        exporter = MarkdownExporter()
        path = await exporter.save("# Test", tmp_path / "test")
        assert path.suffix == ".md"
        assert path.read_text() == "# Test"


class TestTextExporter:
    """TextExporter tests."""

    def test_strips_headers(self) -> None:
        result = TextExporter().export("## Header\nText")
        assert "##" not in result
        assert "Header" in result

    def test_strips_bold(self) -> None:
        result = TextExporter().export("**bold** text")
        assert "**" not in result
        assert "bold" in result

    def test_strips_links(self) -> None:
        result = TextExporter().export("[link](https://example.com)")
        assert "link" in result
        assert "https://" not in result


class TestHtmlExporter:
    """HtmlExporter tests."""

    def test_wraps_in_document(self) -> None:
        result = HtmlExporter().export("<p>Hello</p>")
        assert "<!DOCTYPE html>" in result
        assert "<p>Hello</p>" in result

    def test_uses_metadata_title(self) -> None:
        result = HtmlExporter().export("<p>Hi</p>", {"title": "MyPage"})
        assert "<title>MyPage</title>" in result
