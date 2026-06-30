import asyncio
import logging
from uuid import UUID

from src.core.config import settings

logger = logging.getLogger(__name__)


class JobGate:
    """Limit how many pipeline jobs run concurrently in-process."""

    def __init__(self, max_concurrent: int | None = None) -> None:
        limit = max_concurrent if max_concurrent is not None else settings.MAX_CONCURRENT_JOBS
        self._semaphore = asyncio.Semaphore(limit)
        self._active_jobs: set[str] = set()
        self._lock = asyncio.Lock()

    async def try_acquire(self, job_id: UUID) -> bool:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.001)
        except asyncio.TimeoutError:
            return False

        async with self._lock:
            self._active_jobs.add(str(job_id))
        logger.info("Job gate acquired for %s (%d active)", job_id, len(self._active_jobs))
        return True

    async def release(self, job_id: UUID) -> None:
        job_key = str(job_id)
        async with self._lock:
            if job_key not in self._active_jobs:
                return
            self._active_jobs.remove(job_key)
        self._semaphore.release()
        logger.info("Job gate released for %s (%d active)", job_id, len(self._active_jobs))

    @property
    def active_count(self) -> int:
        return len(self._active_jobs)


job_gate = JobGate()
