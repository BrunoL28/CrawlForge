"""
crawlforge.exporters.html
~~~~~~~~~~~~~~~~~~~~~~~~~~
HTML exporter — wraps content in a minimal HTML document.
"""

from __future__ import annotations

import bleach
import aiofiles
from pathlib import Path
from typing import TYPE_CHECKING

from crawlforge.exporters.base import BaseExporter
from crawlforge.models.enums import OutputFormat

if TYPE_CHECKING:
    from crawlforge.models.schemas import CrawlJob


class HtmlExporter(BaseExporter):
    """Exports content as a sanitized and standalone HTML document."""

    ALLOWED_TAGS = [
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "br", "hr",
        "ul", "ol", "li",
        "blockquote", "pre", "code",
        "em", "strong", "span", "a",
        "table", "thead", "tbody", "tr", "th", "td",
        "img",
    ]
    
    ALLOWED_ATTRS = {
        "a": ["href", "title"],
        "img": ["src", "alt", "title", "width", "height"],
        "*": ["id", "class"],
    }

    @property
    def format(self) -> OutputFormat:
        return OutputFormat.HTML

    @property
    def file_extension(self) -> str:
        return ".html"

    async def export(self, content: str, job: CrawlJob) -> Path:
        """
        Sanitize content with bleach and wrap in minimal HTML.
        """
        sanitized = bleach.clean(
            content,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRS,
            strip=True
        )

        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CrawlForge Export - {job.url}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #333; }}
        pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; border-radius: 4px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f8f8f8; }}
        img {{ max-width: 100%; height: auto; }}
        .metadata {{ color: #666; font-size: 0.9rem; border-bottom: 1px solid #eee; padding-bottom: 1rem; margin-bottom: 2rem; }}
    </style>
</head>
<body>
    <div class="metadata">
        <p><strong>URL:</strong> {job.url}</p>
        <p><strong>Session:</strong> {job.session_id}</p>
        <p><strong>Depth:</strong> {job.depth}</p>
    </div>
    <div class="content">
        {sanitized}
    </div>
</body>
</html>"""

        filename = f"{job.id}{self.file_extension}"
        output_path = Path("output") / str(job.url.host or "unknown") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(html_output)

        return output_path
