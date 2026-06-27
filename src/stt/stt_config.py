import os

MODEL_SIZE = os.getenv("MODEL_SIZE", "base")

DEVICE = os.getenv("DEVICE", "cpu")

COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")

BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "5"))

MAX_CONCURRENT_TRANSCRIPTIONS = int(os.getenv("MAX_CONCURRENT_TRANSCRIPTIONS", "1"))

SUPPORTED_LANGUAGES = ["ar", "en"]