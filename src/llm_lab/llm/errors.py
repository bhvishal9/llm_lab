class LlmError(Exception):
    """Base error for LLM-related failures."""


class LlmAuthenticationError(LlmError):
    """Error raised for authentication failures with the LLM service."""


class LlmRateLimitError(LlmError):
    """Error raised when rate limits are exceeded for the LLM service."""


class LlmUnavailableError(LlmError):
    """Error raised when the LLM service is unavailable."""


class LlmInvalidRequestError(LlmError):
    """Error raised for invalid requests to the LLM service."""
