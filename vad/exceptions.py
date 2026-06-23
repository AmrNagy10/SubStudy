
class VADBaseError(Exception):
    pass

class VADModelLoadingError(VADBaseError):
    pass

class VADInputValidationError(VADBaseError):
    pass

class VADModelProcessingError(VADBaseError):
    pass
