"""Retry utilities with exponential backoff"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import logging
import requests

logger = logging.getLogger(__name__)


def retry_with_backoff(max_attempts=3, multiplier=1, min_wait=1, max_wait=10, exceptions=(Exception,)):
    """
    Generic retry decorator with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        multiplier: Exponential multiplier
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exceptions to retry on
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions)
    )


# Convenience wrappers for specific use cases
retry_api_call = lambda max_attempts=3: retry_with_backoff(
    max_attempts=max_attempts,
    exceptions=(requests.exceptions.RequestException,)
)

retry_openai_call = lambda max_attempts=2: retry_with_backoff(
    max_attempts=max_attempts,
    multiplier=2,
    min_wait=2,
    max_wait=20
)

retry_db_operation = lambda max_attempts=3: retry_with_backoff(
    max_attempts=max_attempts,
    multiplier=0.5,
    min_wait=0.5,
    max_wait=5
)