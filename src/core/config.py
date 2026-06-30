import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "SubStudy"
    API_V1_STR: str = "/api/v1"
    API_KEY: str = "change_me_in_production"
    LOCAL_DEV_MODE: bool = True
    OPENAPI_ENABLED: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    # Storage
    TEMP_DIR: str = "tmp_uploads"
    DB_PATH: str = "substudy_jobs.db"

    # Concurrency
    MAX_CONCURRENT_JOBS: int = 1

    # ML — STT
    MODEL_SIZE: str = "base"
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"
    STT_BEAM_SIZE: int = 5
    MAX_CONCURRENT_TRANSCRIPTIONS: int = 1

    # ML — VAD
    SILERO_VAD_DIR: str = "models/silero-vad"

    # Audio / FFmpeg
    OUTPUT_FORMAT: str = "wav"
    AUDIO_CHANNELS: int = 1
    TARGET_RATE: int = 16000
    FFMPEG_BINARY_PATH: str = "ffmpeg"
    PROCESS_TIMEOUT_SECONDS: int = 300

    # LLM (translation + summary)
    GITHUB_TOKEN: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    LLM_API_BASE: str = "https://models.inference.ai.azure.com"
    LLM_ENDPOINT: str = "https://models.inference.ai.azure.com/chat/completions"
    LLM_MODEL_NAME: str = "gpt-4o"
    TRANSLATION_CHUNK_SIZE: int = 15
    LLM_MIN_REQUEST_INTERVAL: float = 6.5
    LLM_MAX_RETRIES: int = 4
    LLM_RETRY_BASE_DELAY: float = 10.0

    # PRD validation matrix
    MIN_FILE_SIZE_BYTES: int = 10 * 1024
    MAX_FILE_SIZE_BYTES: int = 500 * 1024 * 1024
    MIN_DURATION_SECONDS: float = 3.0
    MAX_DURATION_SECONDS: float = 600.0

    ALLOWED_CONTAINERS: set = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
    ALLOWED_VIDEO_CODECS: set = {"h264", "hevc", "h265", "avc1"}
    ALLOWED_AUDIO_CODECS: set = {"aac", "mp3", "wav"}

    MIN_RESOLUTION_WIDTH: int = 640
    MIN_RESOLUTION_HEIGHT: int = 360
    MAX_RESOLUTION_WIDTH: int = 3840
    MAX_RESOLUTION_HEIGHT: int = 2160

    MIN_FPS: float = 24.0
    MAX_FPS: float = 60.0

    AUDIO_SAMPLE_RATE: int = 16000

    SUPPORTED_SOURCE_LANGS: list = ["English", "Arabic", "Auto"]
    SUPPORTED_TARGET_LANGS: list = ["Arabic", "English"]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
os.makedirs(settings.TEMP_DIR, exist_ok=True)
