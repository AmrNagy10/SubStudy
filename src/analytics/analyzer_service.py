import re
import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from src.core.config import settings
from src.llm.client import llm_client, LLMError
from .exceptions import LLMConnectionError, OutputParsingError, PromptValidationError
from .prompts import SUMMARY_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    short_summary: str
    detailed_summary: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AIAnalyzerService:
    """Semantic summarization via shared LLM client (GitHub Models → Gemini fallback)."""

    def __init__(self):
        if not settings.GITHUB_TOKEN and not settings.GEMINI_API_KEY:
            raise ValueError(
                "GITHUB_TOKEN or GEMINI_API_KEY is required. Set at least one in your .env file."
            )

    async def close(self) -> None:
        pass

    async def _request_summary_text(self, prompt: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise data-processing API. Always output raw JSON. "
                    "Never include markdown formatting like ```json."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        try:
            return await llm_client.chat(messages, temperature=0.0, json_mode=True)
        except LLMError as exc:
            raise LLMConnectionError(str(exc)) from exc

    def _sanitize_and_parse_json(self, raw_text: str) -> dict:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            cleaned = match.group(0).strip()
        else:
            cleaned = raw_text.replace('```json', '').replace('```', '').strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON. Raw: %s", raw_text)
            raise OutputParsingError("LLM output was not valid JSON.") from e

    async def generate_summary(self, transcript_text: str) -> SummaryResult:
        if not transcript_text or len(transcript_text.strip()) < 20:
            raise PromptValidationError("Transcript too short to summarize.")

        prompt = SUMMARY_PROMPT_TEMPLATE.replace('{transcript_text}', transcript_text)

        try:
            logger.info("Sending transcript to LLM for semantic analysis...")
            raw_content = await self._request_summary_text(prompt)
            parsed = self._sanitize_and_parse_json(raw_content)

            short = parsed.get("short_summary", "Could not generate a short summary.")
            raw_details = parsed.get("detailed_summary", [])

            if isinstance(raw_details, list):
                detail_points = [str(item) for item in raw_details]
            elif isinstance(raw_details, str):
                detail_points = [line.strip() for line in raw_details.split('\n') if line.strip()]
            else:
                detail_points = []

            while len(detail_points) < 4:
                detail_points.append("Detailed point unavailable.")
            detail_points = detail_points[:4]

            logger.info("Summary generated and validated successfully.")
            return SummaryResult(short_summary=short, detailed_summary=detail_points)

        except (LLMConnectionError, OutputParsingError) as e:
            logger.warning("Summary generation failed after all LLM providers: %s", e, exc_info=True)
            return SummaryResult(
                short_summary="Summary unavailable",
                detailed_summary=[
                    "Could not generate summary — all LLM providers failed or returned invalid output.",
                    "Check GITHUB_TOKEN and GEMINI_API_KEY in your .env file.",
                    "If you hit rate limits, wait a minute and retry.",
                    "The transcript and subtitles were still saved successfully.",
                ],
            )
