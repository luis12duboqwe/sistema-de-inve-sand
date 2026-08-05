"""Controles de seguridad para autenticación y anti-abuso."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Optional

import jwt
from jwt import PyJWTError as JWTError

from app.config import settings


class LoginAttemptTracker:
    """Trackea intentos fallidos de login por usuario+IP con ventana deslizante."""

    def __init__(self, *, max_attempts: int, block_minutes: int, window_minutes: int = 15) -> None:
        self.max_attempts = max_attempts
        self.block_seconds = block_minutes * 60
        self.window_seconds = window_minutes * 60
        self._lock = Lock()
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._blocked_until: dict[str, float] = {}

    def _cleanup(self, key: str, now_ts: float) -> None:
        cutoff = now_ts - self.window_seconds
        queue = self._failures[key]
        while queue and queue[0] < cutoff:
            queue.popleft()
        if not queue:
            self._failures.pop(key, None)

        blocked_until = self._blocked_until.get(key)
        if blocked_until and blocked_until <= now_ts:
            self._blocked_until.pop(key, None)

    def is_blocked(self, key: str) -> tuple[bool, int]:
        now_ts = time.time()
        with self._lock:
            self._cleanup(key, now_ts)
            blocked_until = self._blocked_until.get(key)
            if not blocked_until:
                return False, 0
            return True, max(0, int(blocked_until - now_ts))

    def register_failure(self, key: str) -> tuple[bool, int]:
        now_ts = time.time()
        with self._lock:
            self._cleanup(key, now_ts)
            queue = self._failures[key]
            queue.append(now_ts)
            if len(queue) >= self.max_attempts:
                unblock_at = now_ts + self.block_seconds
                self._blocked_until[key] = unblock_at
                return True, int(self.block_seconds)
            return False, 0

    def register_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._blocked_until.pop(key, None)


def extract_jwt_subject(authorization_header: Optional[str]) -> Optional[str]:
    """Extrae el `sub` del JWT si el header Authorization es válido."""
    if not authorization_header:
        return None
    parts = authorization_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    if isinstance(subject, str) and subject.strip():
        return subject.strip()
    return None
