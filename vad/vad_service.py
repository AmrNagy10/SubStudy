import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Union
import torch
import torchaudio

from .vad_config import SileroVADConfig
from .vad_client import SileroVADClient
from .exceptions import VADInputValidationError, VADModelProcessingError

# Setup local logger for business logic tracking
logger = logging.getLogger(__name__)


class SileroVADService:
    """
    High-level Orchestrator Service for Voice Activity Detection (VAD).
    Handles file-system interactions, audio decoding, strict input validation,
    and post-processing raw model tensor outputs into seconds.
    """

    def __init__(self, config: SileroVADConfig, client: SileroVADClient):
        self.config = config
        self.client = client

    def _load_and_validate_audio_sync(self, file_path: Path) -> torch.Tensor:
        """
        Synchronous internal boundary to load the audio file from disk
        and enforce strict data contracts required by the AI model.
        """
        if not file_path.exists():
            raise VADInputValidationError(f"Audio file does not exist at path: {file_path}")

        try:
            # Load audio file using torchaudio (Heavy disk I/O and decoding)
            waveform, sample_rate = torchaudio.load(str(file_path))

            # CRITICAL VALIDATION: Enforce standard sampling rate contract
            if sample_rate != self.config.SAMPLE_RATE:
                raise VADInputValidationError(
                    f"Sample rate mismatch. Pipeline expected {self.config.SAMPLE_RATE}Hz, "
                    f"but file provided {sample_rate}Hz."
                )

            # Robust downmixing: If stereo or multichannel, average channels to Mono
            if waveform.shape[0] > 1:
                logger.warning(f"Audio has {waveform.shape[0]} channels. Downmixing to mono for VAD.")
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Silero VAD expects a 1D tensor shape: (samples,)
            audio_tensor = waveform.squeeze(0)
            return audio_tensor

        except VADInputValidationError:
            # Re-raise explicit validation errors to be handled by upstream routers
            raise
        except Exception as e:
            raise VADInputValidationError(f"Failed to decode or parse audio file: {str(e)}")

    def _post_process_timestamps(self, raw_timestamps: List[Dict[str, int]]) -> List[Dict[str, float]]:
        """
        Converts low-level model sample indices into standard clean seconds
        for easy consumption by the frontend and downstream STT engines.
        """
        processed_segments = []
        for segment in raw_timestamps:
            # Formula: second = sample_index / sampling_rate
            start_sec = round(segment["start"] / self.config.SAMPLE_RATE, 2)
            end_sec = round(segment["end"] / self.config.SAMPLE_RATE, 2)

            processed_segments.append({
                "start": start_sec,
                "end": end_sec
            })
        return processed_segments

    async def process_audio_file(self, file_path: Union[str, Path]) -> List[Dict[str, float]]:
        """
        Main asynchronous entrypoint to execute the VAD pipeline on a file.
        Orchestrates cross-layer calls without blocking the FastAPI event loop.
        """
        path_obj = Path(file_path)
        logger.info(f"Initiating VAD pipeline processing for file: {path_obj.name}")

        # 1. Load and validate file on a separate worker thread (Non-blocking I/O)
        audio_tensor = await asyncio.to_thread(self._load_and_validate_audio_sync, path_obj)

        # 2. Delegate the tensor to the low-level AI client for inference
        try:
            raw_timestamps = await self.client.process_audio(audio_tensor)
        except Exception as e:
            # Wrap unexpected low-level exceptions into an engineered domain error
            raise VADModelProcessingError(f"Core VAD processing failed on file {path_obj.name}: {str(e)}")

        # 3. Transform raw matrix samples to functional seconds
        speech_segments = self._post_process_timestamps(raw_timestamps)

        logger.info(
            f"Successfully finalized VAD for {path_obj.name}. "
            f"Extracted {len(speech_segments)} valid speech segments."
        )

        return speech_segments