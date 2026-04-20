"""
crawlforge.exporters.base
~~~~~~~~~~~~~~~~~~~~~~~~~~
Protocol interface for content exporters.
Implement this to add new output formats.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from crawlforge.models.enums import OutputFormat
    from crawlforge.models.schemas import CrawlJob


class BaseExporter(ABC):
    """
    Abstract base class for content exporters.
    """

    @property
    @abstractmethod
    def format(self) -> OutputFormat:
        """The output format this exporter produces."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for the output (e.g., '.md', '.html')."""
        pass

    @abstractmethod
    async def export(self, content: str, job: CrawlJob) -> Path:
        """
        Convert content and save it to disk.

        Args:
            content: The raw or processed content string.
            job: The job associated with this content.

        Returns:
            The path where the file was saved.
        """
        pass
