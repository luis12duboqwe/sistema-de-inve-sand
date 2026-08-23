import jwt

from app.config import settings
from app.utils import auth_security
from app.utils.auth_security import LoginAttemptTracker, extract_jwt_subject


def test_login_attempt_tracker_blocks_at_threshold_and_reports_remaining_time(monkeypatch):
    now = [1_000.0]
    monkeypatch.setattr(auth_security.time, "time", lambda: now[0])
    tracker = LoginAttemptTracker(max_attempts=3, block_minutes=2, window_minutes=15)

    assert tracker.register_failure("user|ip") == (False, 0)
    assert tracker.register_failure("user|ip") == (False, 0)
    assert tracker.register_failure("user|ip") == (True, 120)
    assert tracker.is_blocked("user|ip") == (True, 120)

    now[0] += 31
    blocked, remaining = tracker.is_blocked("user|ip")
    assert blocked is True
    assert remaining == 89


def test_login_attempt_tracker_expires_block_and_old_failure_window(monkeypatch):
    now = [2_000.0]
    monkeypatch.setattr(auth_security.time, "time", lambda: now[0])
    tracker = LoginAttemptTracker(max_attempts=2, block_minutes=1, window_minutes=1)

    assert tracker.register_failure("key") == (False, 0)
    now[0] += 61
    assert tracker.is_blocked("key") == (False, 0)

    # The first failure is outside the sliding window, so this starts a fresh count.
    assert tracker.register_failure("key") == (False, 0)
    assert tracker.is_blocked("key") == (False, 0)


def test_login_attempt_tracker_success_clears_failures_and_block(monkeypatch):
    now = [3_000.0]
    monkeypatch.setattr(auth_security.time, "time", lambda: now[0])
    tracker = LoginAttemptTracker(max_attempts=1, block_minutes=5)

    assert tracker.register_failure("key") == (True, 300)
    assert tracker.is_blocked("key")[0] is True

    tracker.register_success("key")

    assert tracker.is_blocked("key") == (False, 0)
    assert tracker.register_failure("key") == (True, 300)


def test_extract_jwt_subject_accepts_valid_bearer_and_trims_subject():
    token = jwt.encode(
        {"sub": "  user@example.com  "},
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    assert extract_jwt_subject(f"Bearer {token}") == "user@example.com"
    assert extract_jwt_subject(f"bearer {token}") == "user@example.com"


def test_extract_jwt_subject_rejects_missing_malformed_or_invalid_headers():
    assert extract_jwt_subject(None) is None
    assert extract_jwt_subject("") is None
    assert extract_jwt_subject("Token abc") is None
    assert extract_jwt_subject("Bearer") is None
    assert extract_jwt_subject("Bearer   ") is None
    assert extract_jwt_subject("Bearer not-a-jwt") is None


def test_extract_jwt_subject_rejects_wrong_signature_and_empty_subject():
    wrong_signature = jwt.encode(
        {"sub": "someone"},
        "different-secret-for-jwt-regression-test-32-bytes-plus",
        algorithm=settings.algorithm,
    )
    empty_subject = jwt.encode(
        {"sub": "   "},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    non_string_subject = jwt.encode(
        {"sub": 123},
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    assert extract_jwt_subject(f"Bearer {wrong_signature}") is None
    assert extract_jwt_subject(f"Bearer {empty_subject}") is None
    assert extract_jwt_subject(f"Bearer {non_string_subject}") is None
