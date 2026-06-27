
class STTBaseError(Exception):
    pass

class STTModelLoadError(STTBaseError):
    pass

class TranscriptionError(STTBaseError):
    pass

