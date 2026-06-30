import re
import logging
import asyncio
from typing import List, Dict, AsyncGenerator

from src.core.config import settings
from src.llm.client import llm_client, LLMError
from .exceptions import TranslationAPIError, SRTParsingError, TimestampMismatchError
from .prompts import build_translation_prompt

logger = logging.getLogger(__name__)


class TranslationService:
    """Automated AI translation of SRT files with shared rate-limited LLM client."""

    def __init__(self, chunk_size: int | None = None):
        self.chunk_size = chunk_size if chunk_size is not None else settings.TRANSLATION_CHUNK_SIZE

    async def close(self) -> None:
        """No-op — shared LLM client lifecycle is managed by the application."""
        pass

    def _parse_srt(self, srt_content: str) -> List[Dict[str, str]]:
        blocks = []

        srt_content = srt_content.strip()
        if srt_content.startswith("```"):
            lines = srt_content.splitlines()
            if lines[0].startswith("```"):
                lines.pop(0)
            if lines and lines[-1].startswith("```"):
                lines.pop()
            srt_content = "\n".join(lines).strip()

        srt_content = srt_content.replace('\r\n', '\n').replace('\r', '\n')
        raw_blocks = re.split(r'\n\s*\n', srt_content.strip())

        for raw_block in raw_blocks:
            lines = raw_block.strip().split('\n')
            if len(lines) < 3:
                continue

            block_id = lines[0].strip()
            timestamp = lines[1].strip()
            text = '\n'.join(lines[2:]).strip()

            if '-->' not in timestamp:
                raise SRTParsingError(f"Invalid timestamp format detected at block {block_id}: {timestamp}")

            blocks.append({'id': block_id, 'timestamp': timestamp, 'text': text})

        if not blocks:
            raise SRTParsingError("Validation Failed: No valid SRT blocks found in the input.")

        return blocks

    async def _chunk_blocks(self, blocks: List[Dict[str, str]]) -> AsyncGenerator[List[Dict[str, str]], None]:
        for i in range(0, len(blocks), self.chunk_size):
            yield blocks[i: i + self.chunk_size]

    def _blocks_to_srt(self, blocks: List[Dict[str, str]]) -> str:
        return "\n\n".join(
            f"{block['id']}\n{block['timestamp']}\n{block['text']}"
            for block in blocks
        ).strip()

    async def _call_llm(self, source_lang: str, target_lang: str, srt_chunk: str) -> str:
        prompt = build_translation_prompt(source_lang, target_lang, srt_chunk)
        messages = [
            {
                "role": "system",
                "content": "You are a specialized SRT translator. Preserve IDs and timestamps flawlessly.",
            },
            {"role": "user", "content": prompt},
        ]
        try:
            return await llm_client.chat(messages, temperature=0.2, json_mode=False)
        except LLMError as exc:
            raise TranslationAPIError(str(exc)) from exc

    def _validate_and_reconstruct(
        self, original_blocks: List[Dict[str, str]], translated_srt: str
    ) -> List[Dict[str, str]]:
        try:
            translated_blocks = self._parse_srt(translated_srt)
        except SRTParsingError as e:
            raise SRTParsingError(f"LLM returned corrupted SRT structure. Inner error: {str(e)}")

        if len(original_blocks) != len(translated_blocks):
            raise SRTParsingError(
                f"Data Loss Warning: Sent {len(original_blocks)} blocks, LLM returned {len(translated_blocks)} blocks."
            )

        validated_blocks = []
        for orig, trans in zip(original_blocks, translated_blocks):
            if orig['id'] != trans['id']:
                logger.warning(f"ID mismatch auto-corrected. Expected {orig['id']}, got {trans['id']}")

            if orig['timestamp'] != trans['timestamp']:
                raise TimestampMismatchError(
                    f"Timestamp mismatch at block {orig['id']}. Expected: '{orig['timestamp']}', Got: '{trans['timestamp']}'"
                )

            validated_blocks.append({
                'id': orig['id'],
                'timestamp': orig['timestamp'],
                'text': trans['text'],
            })

        return validated_blocks

    async def translate_srt(self, srt_content: str, source_lang: str, target_lang: str) -> str:
        logger.info(f"Initiating translation flow: {source_lang} -> {target_lang}")

        original_blocks = self._parse_srt(srt_content)
        final_blocks = []

        async for chunk in self._chunk_blocks(original_blocks):
            chunk_srt = self._blocks_to_srt(chunk)

            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    translated_chunk_srt = await self._call_llm(source_lang, target_lang, chunk_srt)
                    validated_chunk = self._validate_and_reconstruct(chunk, translated_chunk_srt)
                    final_blocks.extend(validated_chunk)
                    break
                except (SRTParsingError, TimestampMismatchError) as e:
                    if attempt == max_retries:
                        logger.error(f"Failed to translate chunk after {max_retries} retries: {str(e)}")
                        raise
                    logger.warning(
                        f"Chunk translation validation failed on attempt {attempt + 1}: {str(e)}. Retrying..."
                    )
                    await asyncio.sleep(1.0)

        logger.info(f"Successfully translated {len(final_blocks)} SRT blocks.")
        return self._blocks_to_srt(final_blocks)
