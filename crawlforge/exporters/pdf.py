"""
crawlforge.exporters.pdf
~~~~~~~~~~~~~~~~~~~~~~~~~
PDF exporter — placeholder implementation.
Full PDF generation requires an external library (weasyprint, pdfkit, etc.)
which will be integrated in a later phase.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from weasyprint import HTML
from crawlforge.exporters.base import BaseExporter
from crawlforge.models.enums import OutputFormat

if TYPE_CHECKING:
    from crawlforge.models.schemas import CrawlJob


class PdfExporter(BaseExporter):
    """Exports content as PDF using WeasyPrint."""

    @property
    def format(self) -> OutputFormat:
        return OutputFormat.PDF

    @property
    def file_extension(self) -> str:
        return ".pdf"

    async def export(self, content: str, job: CrawlJob) -> Path:
        """
        Convert content to PDF.
        """
        # Minimal HTML wrap if it doesn't look like HTML
        html_content = content
        if not content.strip().lower().startswith("<!doctype") and not content.strip().lower().startswith("<html"):
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: serif; margin: 2cm; line-height: 1.5; }}
                    header {{ border-bottom: 1px solid #ccc; margin-bottom: 1cm; padding-bottom: 0.5cm; font-size: 10pt; color: #666; }}
                    h1 {{ color: #2c3e50; }}
                </style>
            </head>
            <body>
                <header>
                    Source: {job.url} | Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                </header>
                {content}
            </body>
            </html>
            """

        filename = f"{job.id}{self.file_extension}"
        output_path = Path("output") / str(job.url.host or "unknown") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # WeasyPrint's write_pdf is blocking, run in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: HTML(string=html_content).write_pdf(target=str(output_path))
        )

        return output_path
