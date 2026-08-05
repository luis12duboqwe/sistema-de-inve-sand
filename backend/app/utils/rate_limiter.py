"""
Rate limiting utility for preventing abuse.

Supports per-customer, per-IP, and per-endpoint rate limiting.
Uses in-memory storage with sliding windows.
"""

import logging
import time
from collections import deque
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe in-memory rate limiter using a sliding window."""

    def __init__(self, window_seconds: int = 60, max_requests: int = 100):
        """
        Initialize rate limiter.

        Args:
            window_seconds: Time window in seconds for rate limit.
            max_requests: Max requests allowed within the window.
        """
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._requests: Dict[str, deque[float]] = {}
        self._lock = RLock()

    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check whether a request is allowed and return current limit metadata."""
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            requests = self._requests.setdefault(key, deque())

            while requests and requests[0] < cutoff:
                requests.popleft()

            allowed = len(requests) < self.max_requests
            if allowed:
                requests.append(now)

            reset_at = (
                requests[0] + self.window_seconds
                if requests
                else now + self.window_seconds
            )
            remaining = max(0, self.max_requests - len(requests))

            info = {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset_at": datetime.fromtimestamp(reset_at).isoformat(),
                "reset_in_seconds": max(0, int(reset_at - now)),
            }
            return allowed, info

    def reset(self) -> None:
        """Clear all counters.

        Intended for deterministic test isolation and controlled maintenance,
        never as part of the normal request path.
        """
        with self._lock:
            self._requests.clear()

    def cleanup_old_entries(self, older_than_seconds: int = 3600) -> None:
        """Remove keys with no recent activity to limit memory usage."""
        now = time.time()
        cutoff = now - older_than_seconds

        with self._lock:
            to_delete: List[str] = []
            for key, requests in self._requests.items():
                while requests and requests[0] < cutoff:
                    requests.popleft()
                if not requests:
                    to_delete.append(key)

            for key in to_delete:
                del self._requests[key]

        if to_delete:
            logger.debug("Cleaned up %s stale rate limit entries", len(to_delete))


_photo_request_limiter = RateLimiter(window_seconds=60, max_requests=10)
_api_general_limiter = RateLimiter(window_seconds=60, max_requests=100)
_auth_limiter = RateLimiter(window_seconds=300, max_requests=5)


def get_photo_request_limiter() -> RateLimiter:
    """Get the photo request rate limiter."""
    return _photo_request_limiter


def get_api_general_limiter() -> RateLimiter:
    """Get the general API rate limiter."""
    return _api_general_limiter


def get_auth_limiter() -> RateLimiter:
    """Get the authentication rate limiter."""
    return _auth_limiter


def reset_all_limiters() -> None:
    """Reset all counters, primarily to isolate automated tests."""
    _photo_request_limiter.reset()
    _api_general_limiter.reset()
    _auth_limiter.reset()


def cleanup_all_limiters() -> None:
    """Periodic cleanup of stale entries (call from a background job)."""
    _photo_request_limiter.cleanup_old_entries()
    _api_general_limiter.cleanup_old_entries()
    _auth_limiter.cleanup_old_entries()
    logger.debug("Rate limiter cleanup completed")
