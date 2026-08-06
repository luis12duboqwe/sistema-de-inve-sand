from app.utils.rate_limiter import RateLimiter


def test_rate_limiter_blocks_after_limit_and_reset_restores_access():
    limiter = RateLimiter(window_seconds=60, max_requests=2)

    first_allowed, first_info = limiter.is_allowed("client:1")
    second_allowed, second_info = limiter.is_allowed("client:1")
    third_allowed, third_info = limiter.is_allowed("client:1")

    assert first_allowed is True
    assert first_info["remaining"] == 1
    assert second_allowed is True
    assert second_info["remaining"] == 0
    assert third_allowed is False
    assert third_info["remaining"] == 0
    assert third_info["limit"] == 2

    limiter.reset()

    allowed_after_reset, reset_info = limiter.is_allowed("client:1")
    assert allowed_after_reset is True
    assert reset_info["remaining"] == 1


def test_rate_limiter_keeps_subjects_isolated():
    limiter = RateLimiter(window_seconds=60, max_requests=1)

    assert limiter.is_allowed("client:a")[0] is True
    assert limiter.is_allowed("client:a")[0] is False
    assert limiter.is_allowed("client:b")[0] is True
