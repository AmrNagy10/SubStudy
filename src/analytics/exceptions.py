class AIAnalysisBaseError(Exception):

    pass

class LLMConnectionError(AIAnalysisBaseError):
    pass

class OutputParsingError(AIAnalysisBaseError):
    pass

class PromptValidationError(AIAnalysisBaseError):
    pass