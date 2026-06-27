import os

OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "wav")

AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))

TARGET_RATE = int(os.getenv("TARGET_RATE", "16000"))

FFMPEG_BINARY_PATH = os.getenv("FFMPEG_BINARY_PATH", "ffmpeg")

PROCESS_TIMEOUT_SECONDS = int(os.getenv("PROCESS_TIMEOUT_SECONDS", "300"))