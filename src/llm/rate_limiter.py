import asyncio
import time


class LLMRateLimiter:
    """Serialize LLM calls and enforce a minimum gap to stay under provider rate limits."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def wait_turn(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()
