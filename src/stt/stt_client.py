import asyncio
import logging
from faster_whisper import WhisperModel
from .stt_config import MODEL_SIZE, DEVICE, COMPUTE_TYPE, BEAM_SIZE, MAX_CONCURRENT_TRANSCRIPTIONS
from .exceptions import STTModelLoadError, TranscriptionError

logger = logging.getLogger(__name__)

class STTClient:
    def __init__(self):
        logger.info(f"⏳ Loading faster-whisper model '{MODEL_SIZE}' on {DEVICE}...")
        try:
            self.model = WhisperModel(
                model_size_or_path=MODEL_SIZE,
                device=DEVICE,
                compute_type=COMPUTE_TYPE
            )
            logger.info("✅ STT model loaded successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to load STT model: {str(e)}")
            raise STTModelLoadError(f"Model initialization failed: {str(e)}") from e
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSCRIPTIONS)

    def _transcribe_sync(self, audio_input, language=None):
        try:
            segments, info = self.model.transcribe(
                audio=audio_input,
                beam_size=BEAM_SIZE,
                language=language,
                word_timestamps=False
            )
            transcribed_data = [
                {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
                for seg in segments
            ]
            return transcribed_data, info.language
        except Exception as e:
            logger.error(f"❌ Error during transcription: {str(e)}")
            raise TranscriptionError(f"Transcription failed: {str(e)}") from e

    async def transcribe_audio(self, audio_input, language=None):
        async with self._semaphore:
            return await asyncio.to_thread(self._transcribe_sync, audio_input, language)