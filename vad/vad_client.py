import logging
import asyncio
import torch
from typing import List, Dict

from .vad_config import SileroVADConfig
from .exceptions import VADModelLoadingError, VADModelProcessingError

# Setup local logger for this module
logger = logging.getLogger(__name__)


class SileroVADClient:
    """
    Low-level production-ready client for interacting with the Silero VAD PyTorch model.
    Handles dynamic device allocation (CPU/GPU), memory optimization, and async thread boundaries.
    """

    def __init__(self, config: SileroVADConfig):
        self.config = config
        self.model = None
        self.get_speech_timestamps = None

        # Target GPU if available for maximum hardware performance, fallback to CPU
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_model_sync(self) -> None:
            """Synchronous method to safely download and initialize the PyTorch model in memory."""
            try:
                # Route all low-level PyTorch/Hub warnings to standard logging instead of console pollution
                logging.captureWarnings(True)

                model, utils = torch.hub.load(
                    repo_or_dir=self.config.REPO_OR_DIR,
                    model=self.config.MODEL_NAME,
                    force_reload=self.config.FORCE_RELOAD,
                    trust_repo=True  # Explicit safety flag for recent PyTorch versions
                )

                # Move model to the selected compute device and set to evaluation mode
                self.model = model.to(self.device)
                self.model.eval()

                # Extract the core timestamp processing function from Silero utilities
                self.get_speech_timestamps = utils[0]

                logger.info(f"Silero VAD model successfully loaded on device: {self.device}")

            except Exception as e:
                raise VADModelLoadingError(f"Failed to initialize Silero VAD model: {str(e)}")

    async def load_model(self) -> None:
            """
            Asynchronous wrapper to load the model.
            Prevents blocking the main asyncio event loop during heavy I/O or network fetch.
            """
            await asyncio.to_thread(self._load_model_sync)

    def _process_tensor_sync(self, audio_tensor: torch.Tensor) -> List[Dict[str, int]]:
            """Synchronous batch inference with memory optimization."""
            try:
                # Ensure the incoming audio tensor resides on the same device as the neural network
                if audio_tensor.device != self.device:
                    audio_tensor = audio_tensor.to(self.device)

                # Disable gradient tracking to eliminate runtime memory overhead during inference
                with torch.no_grad():
                    timestamps = self.get_speech_timestamps(
                        audio_tensor,
                        self.model,
                        sampling_rate=self.config.SAMPLE_RATE,
                        threshold=self.config.THRESHOLD,
                        min_speech_duration_ms=self.config.MIN_SPEECH_DURATION_MS,
                        min_silence_duration_ms=self.config.MIN_SILENCE_DURATION_MS,
                        speech_pad_ms=self.config.SPEECH_PAD_MS,
                        window_size_samples=self.config.WINDOW_SIZE_SAMPLES
                    )
                return timestamps
            except Exception as e:
                raise VADModelProcessingError(f"Model inference failed: {str(e)}")

            finally:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    async def process_audio(self, audio_tensor: torch.Tensor) -> List[Dict[str, int]]:
            """
            Asynchronous execution boundary for model inference.
            Offloads the heavy CPU/GPU matrix multiplication to worker threads to keep FastAPI responsive.
            """
            if self.model is None or self.get_speech_timestamps is None:
                raise VADModelProcessingError("VAD Model is not initialized. Call load_model() first.")

            return await asyncio.to_thread(self._process_tensor_sync, audio_tensor  )