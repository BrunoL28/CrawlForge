"""
crawlforge.exporters.markdown
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Markdown exporter — adds YAML frontmatter from metadata.
"""

from __future__ import annotations

import yaml
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from crawlforge.exporters.base import BaseExporter
from crawlforge.models.enums import OutputFormat

if TYPE_CHECKING:
    from crawlforge.models.schemas import CrawlJob


class MarkdownExporter(BaseExporter):
    """Exports content as Markdown with YAML frontmatter."""

    @property
    def format(self) -> OutputFormat:
        return OutputFormat.MARKDOWN

    @property
    def file_extension(self) -> str:
        return ".md"

    async def export(self, content: str, job: CrawlJob) -> Path:
        """
        Convert content to Markdown with frontmatter and save.
        """
        metadata = {
            "url": str(job.url),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": job.session_id,
            "depth": job.depth,
        }
        
        frontmatter = yaml.dump(metadata, sort_keys=False)
        formatted_content = f"---\n{frontmatter}---\n\n{content}"

        # Default path in output/ domain / filename
        filename = f"{job.id}{self.file_extension}"
        output_path = Path("output") / str(job.url.host or "unknown") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(formatted_content)

        return output_path
