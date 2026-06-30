import asyncio
import logging

from src.core.config import settings
from src.vad.vad_config import SileroVADConfig
from src.vad.vad_client import SileroVADClient
from src.vad.vad_service import SileroVADService
from src.stt.stt_client import STTClient
from src.stt.stt_service import STTService

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Load VAD and STT models once and reuse across pipeline jobs."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._vad_client: SileroVADClient | None = None
        self._vad_config: SileroVADConfig | None = None
        self._stt_client: STTClient | None = None
        self.vad_loaded = False
        self.stt_loaded = False

    async def get_vad(self) -> SileroVADService:
        async with self._lock:
            if not self.vad_loaded:
                self._vad_config = SileroVADConfig(REPO_OR_DIR=settings.SILERO_VAD_DIR)
                self._vad_client = SileroVADClient(config=self._vad_config)
                await self._vad_client.load_model()
                self.vad_loaded = True
                logger.info("Silero VAD ready (singleton)")
            return SileroVADService(config=self._vad_config, client=self._vad_client)

    async def get_stt(self) -> STTService:
        async with self._lock:
            if not self.stt_loaded:
                self._stt_client = await asyncio.to_thread(STTClient)
                self.stt_loaded = True
                logger.info(
                    "Whisper ready (singleton): %s on %s/%s",
                    settings.MODEL_SIZE,
                    settings.DEVICE,
                    settings.COMPUTE_TYPE,
                )
            return STTService(stt_client=self._stt_client)


model_registry = ModelRegistry()
