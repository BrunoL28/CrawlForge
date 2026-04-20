"""
tests.test_queue
~~~~~~~~~~~~~~~~~
Validate the async priority queue with retry/backoff.
"""

from __future__ import annotations

import pytest

from crawlforge.config.settings import Settings
from crawlforge.models.enums import JobStatus
from crawlforge.models.schemas import CrawlJob
from crawlforge.queue.manager import JobQueue


@pytest.fixture
def settings() -> Settings:
    return Settings(
        queue_max_retries=2,
        queue_backoff_base=0.01,  # Fast for tests
        queue_backoff_max=0.1,
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture
def queue(settings: Settings) -> JobQueue:
    return JobQueue(settings)


class TestJobQueue:
    """JobQueue async tests."""

    @pytest.mark.asyncio
    async def test_submit_and_next(self, queue: JobQueue) -> None:
        """Submitted jobs should be dequeued in priority order."""
        low = CrawlJob(url="https://example.com/low", priority=7)
        high = CrawlJob(url="https://example.com/high", priority=1)

        await queue.submit(low)
        await queue.submit(high)

        assert queue.size == 2

        first = await queue.next()
        assert first.id == high.id
        assert first.status == JobStatus.RUNNING

        second = await queue.next()
        assert second.id == low.id

    @pytest.mark.asyncio
    async def test_complete(self, queue: JobQueue) -> None:
        """Completing a job should set status."""
        job = CrawlJob(url="https://example.com")
        await queue.submit(job)
        await queue.next()
        await queue.complete(job.id)

        tracked = queue.get_job(job.id)
        assert tracked is not None
        assert tracked.status == JobStatus.COMPLETED
        assert tracked.completed_at is not None

    @pytest.mark.asyncio
    async def test_fail_and_retry(self, queue: JobQueue) -> None:
        """Failing should re-queue if retries remain."""
        job = CrawlJob(url="https://example.com", max_retries=2)
        await queue.submit(job)
        await queue.next()

        retried = await queue.fail(job.id, "timeout")
        assert retried is True
        assert queue.size == 1

    @pytest.mark.asyncio
    async def test_fail_permanently(self, queue: JobQueue) -> None:
        """Job should fail permanently after exhausting retries."""
        job = CrawlJob(url="https://example.com", max_retries=1)
        await queue.submit(job)
        await queue.next()  # attempt 1

        # Fail once — should retry
        await queue.fail(job.id, "error1")
        await queue.next()  # attempt 2

        # Fail again — should be permanent
        retried = await queue.fail(job.id, "error2")
        assert retried is False

        tracked = queue.get_job(job.id)
        assert tracked is not None
        assert tracked.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_cancel(self, queue: JobQueue) -> None:
        """Cancelling a queued job should set CANCELLED status."""
        job = CrawlJob(url="https://example.com")
        await queue.submit(job)

        ok = await queue.cancel(job.id)
        assert ok is True

        tracked = queue.get_job(job.id)
        assert tracked is not None
        assert tracked.status == JobStatus.CANCELLED
