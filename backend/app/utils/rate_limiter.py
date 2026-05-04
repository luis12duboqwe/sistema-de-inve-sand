"""
Rate limiting utility for preventing abuse.

Supports per-customer, per-IP, and per-endpoint rate limiting.
Uses in-memory storage with sliding windows.
"""

import time
import logging
from typing import Dict, List, Tuple, Any
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter using sliding window."""
    
    def __init__(self, window_seconds: int = 60, max_requests: int = 100):
        """
        Initialize rate limiter.
        
        Args:
            window_seconds: Time window in seconds for rate limit
            max_requests: Max requests allowed within window
        """
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        # Key -> deque of timestamps (requests within current window)
        self._requests: Dict[str, deque[float]] = {}
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Identifier (customer_id, IP, etc)
        
        Returns:
            (allowed: bool, info: dict with remaining, reset_at)
        """
        now = time.time()
        cutoff = now - self.window_seconds
        
        if key not in self._requests:
            self._requests[key] = deque()
        
        # Remove old requests outside current window
        while self._requests[key] and self._requests[key][0] < cutoff:
            self._requests[key].popleft()
        
        current_count = len(self._requests[key])
        remaining = max(0, self.max_requests - current_count)
        reset_at = (self._requests[key][0] + self.window_seconds) if self._requests[key] else (now + self.window_seconds)
        
        info = {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset_at": datetime.fromtimestamp(reset_at).isoformat(),
            "reset_in_seconds": max(0, int(reset_at - now))
        }
        
        if current_count < self.max_requests:
            self._requests[key].append(now)
            return True, info
        else:
            return False, info
    
    def cleanup_old_entries(self, older_than_seconds: int = 3600) -> None:
        """Remove keys with no recent activity (memory cleanup)."""
        now = time.time()
        cutoff = now - older_than_seconds
        
        to_delete: List[str] = []
        for key, requests in self._requests.items():
            # Remove timestamps older than cutoff
            while requests and requests[0] < cutoff:
                requests.popleft()
            # Delete key if no requests left
            if not requests:
                to_delete.append(key)
        
        for key in to_delete:
            del self._requests[key]
        
        if to_delete:
            logger.debug(f"Cleaned up {len(to_delete)} stale rate limit entries")


# Global rate limiters for different endpoints/scopes
_photo_request_limiter = RateLimiter(window_seconds=60, max_requests=10)  # 10 per minute per customer
_api_general_limiter = RateLimiter(window_seconds=60, max_requests=100)   # 100 per minute per customer
_auth_limiter = RateLimiter(window_seconds=300, max_requests=5)           # 5 per 5 minutes per IP


def get_photo_request_limiter() -> RateLimiter:
    """Get the photo request rate limiter."""
    return _photo_request_limiter


def get_api_general_limiter() -> RateLimiter:
    """Get the general API rate limiter."""
    return _api_general_limiter


def get_auth_limiter() -> RateLimiter:
    """Get the authentication rate limiter."""
    return _auth_limiter


def cleanup_all_limiters():
    """Periodic cleanup of stale entries (call from a background job)."""
    _photo_request_limiter.cleanup_old_entries()
    _api_general_limiter.cleanup_old_entries()
    _auth_limiter.cleanup_old_entries()
    logger.debug("Rate limiter cleanup completed")
