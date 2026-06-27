from dataclasses import dataclass

@dataclass(frozen=True)
class SileroVADConfig:
    REPO_OR_DIR: str = "models/silero-vad"
    SOURCE: str = "local"
    MODEL_NAME: str = "silero_vad"
    FORCE_RELOAD: bool = False

    SAMPLE_RATE: int = 16000

    WINDOW_SIZE_SAMPLES: int = 512

    # VAD Logic Thresholds
    THRESHOLD: float = 0.5
    MIN_SPEECH_DURATION_MS: int = 250
    MIN_SILENCE_DURATION_MS: int = 100
    SPEECH_PAD_MS: int = 30

