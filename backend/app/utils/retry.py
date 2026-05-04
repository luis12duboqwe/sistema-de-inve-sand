"""
Error recovery and retry utilities with exponential backoff.
"""

import asyncio
import logging
from typing import Callable, TypeVar, Any, Coroutine, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def async_retry(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    **kwargs: Any
) -> T:
    """
    Execute async function with exponential backoff retry.
    
    Args:
        func: Async function to call
        max_attempts: Number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay on each retry
    """
    last_error: Optional[Exception] = None
    delay = initial_delay
    
    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            attempt_num = attempt + 1
            
            if attempt_num >= max_attempts:
                logger.error(f"❌ Retry failed after {max_attempts} attempts: {e}")
                raise
            
            # Cap delay at max_delay
            delay = min(delay, max_delay)
            logger.warning(f"⚠️  Retry attempt {attempt_num}/{max_attempts} failed, retrying in {delay}s: {e}")
            
            await asyncio.sleep(delay)
            delay *= backoff_factor
    
    raise last_error if last_error is not None else Exception("Unknown error")


def sync_retry(max_attempts: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """Decorator for sync functions with retry logic."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error = None
            delay = initial_delay
            
            last_error_sync: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error_sync = e
                    if attempt + 1 >= max_attempts:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{max_attempts}: {e}")
                    import time as _time
                    _time.sleep(delay)
                    delay *= backoff_factor
            
            raise last_error_sync if last_error_sync is not None else Exception("Unknown error")
        return wrapper
    return decorator
