class CoreError(Exception):
    """Base exception for all core functionality errors."""
    pass

class VideoValidationError(CoreError):
    """Raised when a video fails PRD validation checks."""
    pass
