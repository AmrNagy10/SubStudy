
class TranslationError(Exception):
    pass

class TranslationAPIError(TranslationError):
    """Handles external LLM API timeouts or unauthorized errors."""
    pass

class SRTParsingError(TranslationError):
    """"Triggered if the input/output SRT format is corrupted."""
    pass

class TimestampMismatchError(TranslationError):
    """Triggered if the LLM alters or loses original timestamps."""
    pass
