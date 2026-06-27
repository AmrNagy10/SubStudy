# Error Handling

class AudioExtractionError(Exception):
    "Unexpected Errors"
    pass

class FFmpegExecutionError(AudioExtractionError):
    "To handle FFmpeg Errors"
    pass

class AudioTimeoutError(AudioExtractionError):
    "To handle timeouts"
    pass