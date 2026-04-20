"""
crawlforge.exporters.text
~~~~~~~~~~~~~~~~~~~~~~~~~~
Plain-text exporter — strips markdown formatting.
"""

from __future__ import annotations

import html2text
import aiofiles
from pathlib import Path
from typing import TYPE_CHECKING

from crawlforge.exporters.base import BaseExporter
from crawlforge.models.enums import OutputFormat

if TYPE_CHECKING:
    from crawlforge.models.schemas import CrawlJob


class TextExporter(BaseExporter):
    """Exports content as clean plain text, removing HTML/Markdown boilerplate."""

    def __init__(self) -> None:
        self.converter = html2text.HTML2Text()
        self.converter.ignore_links = True
        self.converter.ignore_images = True
        self.converter.ignore_emphasis = True
        self.converter.ignore_tables = True
        self.converter.body_width = 0  # No wrapping

    @property
    def format(self) -> OutputFormat:
        return OutputFormat.TEXT

    @property
    def file_extension(self) -> str:
        return ".txt"

    async def export(self, content: str, job: CrawlJob) -> Path:
        """
        Convert content to plain text using html2text.
        """
        # If content is markdown, html2text still works reasonably well or we can treat it as pseudo-HTML
        text = self.converter.handle(content)

        # Basic metadata header
        header = f"SOURCE: {job.url}\nSESSION: {job.session_id}\nDATE: {datetime.now().isoformat()}\n{'-'*40}\n\n"
        final_content = header + text

        filename = f"{job.id}{self.file_extension}"
        output_path = Path("output") / str(job.url.host or "unknown") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(final_content)

        return output_path

from datetime import datetime
