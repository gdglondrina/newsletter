"""
Error handling utilities with retry logic and exponential backoff.
"""

import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


class APIError(Exception):
    """Base exception for API-related errors."""
    def __init__(self, message: str, status_code: int = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class TransientError(APIError):
    """Transient errors that should be retried (network, timeout, rate limit)."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, status_code, retryable=True)


class FatalError(APIError):
    """Fatal errors that should not be retried (auth, invalid input)."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, status_code, retryable=False)


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (TransientError, ConnectionError, TimeoutError),
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exceptions that trigger a retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
                        raise
                except Exception as e:
                    # Non-retryable exception, raise immediately
                    logger.error(f"Non-retryable error: {e}")
                    raise

            raise last_exception
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handling for the pipeline."""

    @staticmethod
    def handle_api_error(error: Exception, context: str = "") -> dict:
        """
        Analyze an API error and return structured error info.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            dict with error details and recovery suggestions
        """
        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "retryable": False,
            "suggestion": "",
        }

        error_str = str(error).lower()

        # Rate limiting
        if "rate limit" in error_str or "429" in error_str:
            error_info["retryable"] = True
            error_info["suggestion"] = "Wait and retry with exponential backoff"

        # Authentication errors
        elif "unauthorized" in error_str or "401" in error_str or "invalid api key" in error_str:
            error_info["suggestion"] = "Check API key in .env file"

        # Quota errors
        elif "quota" in error_str or "insufficient" in error_str:
            error_info["suggestion"] = "Check API quota/billing status"

        # Network errors
        elif "timeout" in error_str or "connection" in error_str:
            error_info["retryable"] = True
            error_info["suggestion"] = "Check network connection and retry"

        # File not found
        elif "not found" in error_str or "404" in error_str:
            error_info["suggestion"] = "Verify the resource URL/path exists"

        # Server errors
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            error_info["retryable"] = True
            error_info["suggestion"] = "Server error - wait and retry"

        else:
            error_info["suggestion"] = "Check logs for details"

        logger.error(f"API Error [{context}]: {error_info}")
        return error_info

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Check if an error should be retried."""
        if isinstance(error, TransientError):
            return True
        if isinstance(error, FatalError):
            return False

        error_str = str(error).lower()
        retryable_patterns = [
            "rate limit", "429", "timeout", "connection",
            "500", "502", "503", "504", "temporary"
        ]
        return any(pattern in error_str for pattern in retryable_patterns)
