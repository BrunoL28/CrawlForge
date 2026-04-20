"""
tests.test_models
~~~~~~~~~~~~~~~~~~
Validate Pydantic models: CrawlJob, SelectorSchema, enums.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from crawlforge.models.enums import ExtractionStrategy, JobStatus, OutputFormat
from crawlforge.models.schemas import CrawlJob, CrawlRequest, SelectorSchema


class TestCrawlJob:
    """CrawlJob model tests."""

    def test_defaults(self) -> None:
        """Job should have sane defaults."""
        job = CrawlJob(url="https://example.com")
        assert job.strategy == "full"
        assert job.output_format == "md"
        assert job.depth == 0
        assert job.priority == 5
        assert job.max_retries == 3
        assert job.status == "pending"
        assert job.attempts == 0
        assert job.id  # auto-generated

    def test_url_validation(self) -> None:
        """Invalid URLs should raise ValidationError."""
        with pytest.raises(ValidationError):
            CrawlJob(url="not-a-url")

    def test_depth_range(self) -> None:
        """Depth must be 0-5."""
        with pytest.raises(ValidationError):
            CrawlJob(url="https://example.com", depth=10)

    def test_priority_range(self) -> None:
        """Priority must be 1-10."""
        with pytest.raises(ValidationError):
            CrawlJob(url="https://example.com", priority=0)
        with pytest.raises(ValidationError):
            CrawlJob(url="https://example.com", priority=11)

    def test_session_id_generated(self) -> None:
        """Each job should get a unique session_id."""
        job1 = CrawlJob(url="https://example.com")
        job2 = CrawlJob(url="https://example.com")
        assert job1.session_id != job2.session_id


class TestSelectorSchema:
    """SelectorSchema model tests."""

    def test_from_dict(self) -> None:
        """Should parse from dict with baseSelector alias."""
        schema = SelectorSchema(
            name="test",
            baseSelector="div.item",
            fields=[
                {"name": "title", "selector": "h2", "type": "text"},
            ],
        )
        assert schema.base_selector == "div.item"
        assert len(schema.fields) == 1

    def test_requires_base_selector(self) -> None:
        """base_selector is required."""
        with pytest.raises(ValidationError):
            SelectorSchema(name="test", fields=[])


class TestEnums:
    """Enum value tests."""

    def test_extraction_strategies(self) -> None:
        assert ExtractionStrategy.CSS.value == "css"
        assert ExtractionStrategy.HTML.value == "html"
        assert ExtractionStrategy.FULL.value == "full"

    def test_output_formats(self) -> None:
        assert OutputFormat.MARKDOWN.value == "md"
        assert OutputFormat.HTML.value == "html"
        assert OutputFormat.PDF.value == "pdf"
        assert OutputFormat.TEXT.value == "txt"

    def test_job_statuses(self) -> None:
        assert len(JobStatus) == 7
