import re
import httpx
import logging
import asyncio
from typing import List, Dict, AsyncGenerator

# استدعاء ملف الـ exceptions الخاص بك بالمللي
from .exceptions import TranslationAPIError, SRTParsingError, TimestampMismatchError
from .prompts import build_translation_prompt

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Service responsible for automated AI translation of SRT files.
    Fully optimized to work with standard positional exception signatures.
    """

    def __init__(self, api_base_url: str, api_key: str, model: str, chunk_size: int = 50):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.chunk_size = chunk_size

        # Connection Pooling (Keep-Alive) متوافق مع الـ Architecture للمشروع
        self.client = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )

    async def close(self) -> None:
        """Closes the HTTP connection pool securely."""
        await self.client.aclose()
        logger.info("TranslationService HTTP client closed securely.")

    def _parse_srt(self, srt_content: str) -> List[Dict[str, str]]:
        """Parses raw SRT string into a list of block dictionaries."""
        blocks = []

        # ✅ خطوة دفاعية: إزالة علامات الماركداون (```srt أو ```) إذا قام الـ LLM بإضافتها عن طريق الخطأ
        srt_content = srt_content.strip()
        if srt_content.startswith("```"):
            lines = srt_content.splitlines()
            if lines[0].startswith("```"):
                lines.pop(0)  # حذف السطر الأول المعتوي على ```
            if lines and lines[-1].startswith("```"):
                lines.pop()  # حذف السطر الأخير المحتوي على ```
            srt_content = "\n".join(lines).strip()

        # تكملة الكود القديم كما هو بدون أي تغيير
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

            blocks.append({
                'id': block_id,
                'timestamp': timestamp,
                'text': text
            })

        if not blocks:
            raise SRTParsingError("Validation Failed: No valid SRT blocks found in the input.")

        return blocks

    async def _chunk_blocks(self, blocks: List[Dict[str, str]]) -> AsyncGenerator[List[Dict[str, str]], None]:
        """Splits parsed blocks into optimal contextual chunks."""
        for i in range(0, len(blocks), self.chunk_size):
            yield blocks[i: i + self.chunk_size]

    def _blocks_to_srt(self, blocks: List[Dict[str, str]]) -> str:
        """Reconstructs standard dict blocks back to raw SRT string."""
        return "\n\n".join(
            f"{block['id']}\n{block['timestamp']}\n{block['text']}"
            for block in blocks
        ).strip()

    async def _call_llm(self, source_lang: str, target_lang: str, srt_chunk: str) -> str:
        """Calls the LLM API asynchronously using the corrected GitHub Models path."""
        prompt = build_translation_prompt(source_lang, target_lang, srt_chunk)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a specialized SRT translator. Preserve IDs and timestamps flawlessly."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            # مسار الـ Endpoint الصحيح لـ GitHub Models
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP Error: {e.response.status_code}")
            # ✅ متوافق تماماً: نص فقط بدون keyword arguments
            raise TranslationAPIError(f"LLM API returned HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Network error calling LLM: {str(e)}")
            raise TranslationAPIError(f"Network Connection Error: {str(e)}")
        except (KeyError, IndexError):
            raise TranslationAPIError("Malformed JSON structure received from LLM API.")

    def _validate_and_reconstruct(self, original_blocks: List[Dict[str, str]], translated_srt: str) -> List[
        Dict[str, str]]:
        """Strictly compares the LLM output against original data for absolute integrity."""
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

            # ✅ متوافق تماماً: تمرير تفاصيل الخطأ داخل الـ String نفسه لمنع الـ TypeError
            if orig['timestamp'] != trans['timestamp']:
                raise TimestampMismatchError(
                    f"Timestamp mismatch at block {orig['id']}. Expected: '{orig['timestamp']}', Got: '{trans['timestamp']}'"
                )

            validated_blocks.append({
                'id': orig['id'],
                'timestamp': orig['timestamp'],
                'text': trans['text']
            })

        return validated_blocks

    async def translate_srt(self, srt_content: str, source_lang: str, target_lang: str) -> str:
        """Main entry point for translation pipeline."""
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
                    logger.warning(f"Chunk translation validation failed on attempt {attempt + 1}: {str(e)}. Retrying...")
                    await asyncio.sleep(1.0)

        logger.info(f"Successfully translated {len(final_blocks)} SRT blocks.")
        return self._blocks_to_srt(final_blocks)