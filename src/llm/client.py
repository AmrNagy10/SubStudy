import re
import logging
import asyncio

import httpx

from src.core.config import settings
from src.llm.rate_limiter import LLMRateLimiter

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """All configured LLM providers failed."""


class LLMClient:
    """Primary: GitHub Models (GPT). Fallback: Google Gemini. Includes rate limiting and 429 retries."""

    def __init__(self) -> None:
        self._limiter = LLMRateLimiter(settings.LLM_MIN_REQUEST_INTERVAL)
        self._http = httpx.AsyncClient(timeout=90.0)

    async def close(self) -> None:
        await self._http.aclose()

    @staticmethod
    def _parse_retry_seconds(text: str) -> float | None:
        match = re.search(r"wait (\d+) seconds?", text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    async def _call_github(self, messages: list[dict], temperature: float, json_mode: bool) -> str:
        payload: dict = {
            "model": settings.LLM_MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            payload["max_tokens"] = 1500

        response = await self._http.post(
            settings.LLM_ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    async def _call_gemini(self, messages: list[dict], temperature: float, json_mode: bool) -> str:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        user_text = "\n\n".join(m["content"] for m in messages if m["role"] == "user")
        prompt = f"{system}\n\n{user_text}".strip() if system else user_text

        generation_config: dict = {"temperature": temperature}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        response = await self._http.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": generation_config,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    async def _call_github_with_retries(self, messages: list[dict], temperature: float, json_mode: bool) -> str:
        last_error: Exception | None = None
        for attempt in range(settings.LLM_MAX_RETRIES):
            try:
                await self._limiter.wait_turn()
                return await self._call_github(messages, temperature, json_mode)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    wait = (
                        self._parse_retry_seconds(exc.response.text)
                        or settings.LLM_RETRY_BASE_DELAY * (attempt + 1)
                    )
                    logger.warning(
                        "GitHub Models rate limited (429). Waiting %.0fs (attempt %d/%d)",
                        wait,
                        attempt + 1,
                        settings.LLM_MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise
            except httpx.RequestError as exc:
                last_error = exc
                raise
        if last_error:
            raise last_error
        raise LLMError("GitHub Models retries exhausted")

    async def chat(self, messages: list[dict], temperature: float = 0.2, json_mode: bool = False) -> str:
        if not settings.GITHUB_TOKEN and not settings.GEMINI_API_KEY:
            raise LLMError("No LLM API keys configured (GITHUB_TOKEN or GEMINI_API_KEY).")

        github_error: Exception | None = None
        if settings.GITHUB_TOKEN:
            try:
                return await self._call_github_with_retries(messages, temperature, json_mode)
            except Exception as exc:
                github_error = exc
                logger.warning("GitHub Models failed: %s", exc)

        if settings.GEMINI_API_KEY:
            try:
                await self._limiter.wait_turn()
                logger.info("Falling back to Gemini (%s)", settings.GEMINI_MODEL)
                return await self._call_gemini(messages, temperature, json_mode)
            except Exception as exc:
                logger.error("Gemini fallback failed: %s", exc)
                raise LLMError(f"GitHub failed ({github_error}); Gemini failed ({exc})") from exc

        raise LLMError(f"GitHub Models failed and no Gemini fallback configured: {github_error}")


llm_client = LLMClient()
