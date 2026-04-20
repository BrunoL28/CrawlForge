"""
crawlforge.queue.manager
~~~~~~~~~~~~~~~~~~~~~~~~~
In-memory priority queue with:
- Priority ordering (lower number = higher priority)
- Retry with exponential backoff
- Job status tracking
- Async-safe with asyncio.PriorityQueue

Production use should swap this for Redis-backed queues.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Awaitable

from loguru import logger

from crawlforge.models.enums import JobStatus
from crawlforge.models.schemas import CrawlJob

if TYPE_CHECKING:
    from crawlforge.config.settings import Settings


class _PriorityItem:
    """Wrapper for priority queue ordering."""
    def __init__(self, priority: int, timestamp: float, job: CrawlJob) -> None:
        self.priority = priority
        self.timestamp = timestamp
        self.job = job

    def __lt__(self, other: _PriorityItem) -> bool:
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority < other.priority


class QueueManager:
    """
    Manages an internal PriorityQueue and a pool of workers to process CrawlJobs.
    """

    def __init__(self, settings: Settings, processor: Callable[[CrawlJob], Awaitable[None]]) -> None:
        self.settings = settings
        self.processor = processor
        self._queue: asyncio.PriorityQueue[_PriorityItem] = asyncio.PriorityQueue()
        self._jobs: dict[str, CrawlJob] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return
        self._running = True
        num_workers = self.settings.queue_num_workers
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info("QueueManager started with {} workers", num_workers)

    async def stop(self) -> None:
        """Stop all workers."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        logger.info("QueueManager stopped")

    async def add_job(self, job: CrawlJob) -> None:
        """Add a single job to the queue."""
        job.status = JobStatus.QUEUED
        self._jobs[job.id] = job
        item = _PriorityItem(job.priority, time.monotonic(), job)
        await self._queue.put(item)
        logger.info("Job PENDING -> QUEUED: id={} url={}", job.id, job.url)

    async def add_batch(self, urls: list[str], config_template: dict) -> list[str]:
        """
        Add a batch of URLs to the queue using a template config.
        """
        job_ids = []
        for url in urls:
            # Simple conversion from dict template to CrawlJob
            # In a real app, config_template would be a CrawlRequest or similar
            job = CrawlJob(url=url, **config_template)
            await self.add_job(job)
            job_ids.append(job.id)
        return job_ids

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop that pulls and processes jobs."""
        logger.debug("Worker {} started", worker_id)
        while self._running:
            try:
                item = await self._queue.get()
                job = item.job
                
                # Transition: QUEUED -> RUNNING
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                job.attempts += 1
                logger.info("Job QUEUED -> RUNNING: id={} attempt={}", job.id, job.attempts)

                try:
                    await self.processor(job)
                    # Transition: RUNNING -> DONE
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.now(timezone.utc)
                    logger.info("Job RUNNING -> DONE: id={}", job.id)
                except Exception as e:
                    logger.error("Job error: id={} error={}", job.id, str(e))
                    await self._handle_failure(job, str(e))
                finally:
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Unexpected error in worker {}: {}", worker_id, str(e))
                await asyncio.sleep(1)

    async def _handle_failure(self, job: CrawlJob, error: str) -> None:
        """Handle job failure with exponential backoff and retries."""
        job.error_message = error
        
        if job.attempts < self.settings.queue_max_retries + 1:
            # Transition: RUNNING -> RETRYING
            job.status = JobStatus.RETRYING
            delay = self.settings.queue_backoff_base ** (job.attempts - 1)
            delay = min(delay, self.settings.queue_backoff_max)
            
            logger.warning("Job RUNNING -> RETRYING: id={} delay={}s", job.id, delay)
            
            # Re-enqueue after delay
            async def re_enqueue():
                await asyncio.sleep(delay)
                item = _PriorityItem(job.priority, time.monotonic(), job)
                await self._queue.put(item)
                job.status = JobStatus.QUEUED
                logger.info("Job RETRYING -> QUEUED: id={}", job.id)

            asyncio.create_task(re_enqueue())
        else:
            # Transition: RUNNING -> FAILED
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            logger.error("Job RUNNING -> FAILED: id={} max_attempts reached", job.id)

    def get_job_status(self, job_id: str) -> JobStatus | None:
        job = self._jobs.get(job_id)
        return job.status if job else None
