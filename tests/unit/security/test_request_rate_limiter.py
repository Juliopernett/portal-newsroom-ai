from datetime import UTC, datetime, timedelta

from security.request_rate_limiter import RequestRateLimiter


def test_blocks_after_quota_and_recovers_after_window() -> None:
    limiter = RequestRateLimiter(max_eventos=2, ventana=timedelta(minutes=1))
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    assert limiter.permitir("ip", ahora=t0)
    assert limiter.permitir("ip", ahora=t0)
    assert not limiter.permitir("ip", ahora=t0)
    assert limiter.permitir("ip", ahora=t0 + timedelta(minutes=2))
