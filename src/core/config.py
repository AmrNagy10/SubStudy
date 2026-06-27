import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "SubStudy"
    API_V1_STR: str = "/api/v1"
    API_KEY: str = "change_me_in_production"
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000", "null"]

    # Storage Configuration
    TEMP_DIR: str = "tmp_uploads"

    # PRD Functional Validation Criteria Matrix
    MIN_FILE_SIZE_BYTES: int = 10 * 1024  # 10 KB
    MAX_FILE_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB

    MIN_DURATION_SECONDS: float = 3.0
    MAX_DURATION_SECONDS: float = 600.0  # 10 minutes maximum for MVP

    ALLOWED_CONTAINERS: set = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
    ALLOWED_VIDEO_CODECS: set = {"h264", "hevc", "h265", "avc1"}
    ALLOWED_AUDIO_CODECS: set = {"aac", "mp3", "wav"}

    MIN_RESOLUTION_WIDTH: int = 640
    MIN_RESOLUTION_HEIGHT: int = 360
    MAX_RESOLUTION_WIDTH: int = 3840
    MAX_RESOLUTION_HEIGHT: int = 2160

    MIN_FPS: float = 24.0
    MAX_FPS: float = 60.0

    # Audio Extraction ML Specifications
    AUDIO_SAMPLE_RATE: int = 16000  # 16kHz Gold Standard for ML
    AUDIO_CHANNELS: int = 1  # Mono stream

    # Language Options
    SUPPORTED_SOURCE_LANGS: list = ["English", "Arabic", "Auto"]
    SUPPORTED_TARGET_LANGS: list = ["Arabic", "English"]

    class Config:
        case_sensitive = True


# Global settings instance
settings = Settings()

# Ensure temp directory exists safely on initialization
os.makedirs(settings.TEMP_DIR, exist_ok=True)