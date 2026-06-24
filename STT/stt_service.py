import asyncio
import logging
import soundfile as sf
import numpy as np

from .exceptions import TranscriptionError

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self, stt_client):
        self.stt_client = stt_client
        logger.info("✅ STTService initialized.")

    async def process_audio(self, audio_path: str, speech_segments: list, language: str = None) -> list:
        logger.info(f"🎧 Starting STT processing for {audio_path} with {len(speech_segments)} segments.")

        try:
            audio_data, sample_rate = sf.read(audio_path, dtype='float32')
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
        except Exception as e:
            logger.error(f"❌ Failed to read audio file {audio_path}: {e}")
            raise TranscriptionError(f"Audio read error: {e}") from e

        TARGET_SAMPLE_RATE = 16000
        if sample_rate != TARGET_SAMPLE_RATE:
            logger.warning(f"⚠️ Resampling from {sample_rate}Hz to {TARGET_SAMPLE_RATE}Hz")
            try:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=TARGET_SAMPLE_RATE)
                sample_rate = TARGET_SAMPLE_RATE
            except ImportError:
                logger.error("❌ librosa not installed. Install it with: pip install librosa")
                raise

        MIN_CHUNK_DURATION = 0.3  # 🆕 تجاهل المقاطع القصيرة جداً
        tasks = []
        for i, segment in enumerate(speech_segments):
            start_time = segment['start']
            end_time = segment['end']

            # 🆕 تجاهل المقاطع القصيرة
            if (end_time - start_time) < MIN_CHUNK_DURATION:
                logger.debug(f"⏭️ Skipping chunk {i} - too short ({end_time - start_time:.2f}s)")
                continue

            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            audio_chunk = audio_data[start_sample:end_sample]

            tasks.append(self._process_chunk(audio_chunk, start_time, i, language))

        logger.info(f"🚀 Sending {len(tasks)} chunks to STT Client...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_transcript = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.warning(f"⚠️ Chunk {i} failed: {type(res).__name__}: {str(res)}")
                continue
            if res is None:
                logger.warning(f"⚠️ Chunk {i} returned None")
                continue
            final_transcript.extend(res)

        final_transcript = sorted(final_transcript, key=lambda x: x['start'])
        logger.info(f"🎉 STT processing completed. Generated {len(final_transcript)} text segments.")
        return final_transcript

    async def _process_chunk(self, audio_chunk, original_start_time, chunk_index, language):
        logger.debug(f"⚙️ Processing chunk {chunk_index}...")

        transcribed_data, detected_lang = await self.stt_client.transcribe_audio(
            audio_input=audio_chunk,
            language=language
        )

        shifted_data = []
        for item in transcribed_data:
            shifted_data.append({
                "start": round(item['start'] + original_start_time, 2),
                "end": round(item['end'] + original_start_time, 2),
                "text": item['text']
            })

        return shifted_data