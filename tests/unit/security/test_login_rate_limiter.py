"""Unit tests for LoginRateLimiter — pure, no I/O, time injected via `ahora`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from security.login_rate_limiter import LoginRateLimiter

_T0 = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _limiter() -> LoginRateLimiter:
    return LoginRateLimiter(max_intentos=5, ventana=timedelta(minutes=15))


def test_not_blocked_with_no_attempts() -> None:
    limiter = _limiter()

    assert limiter.esta_bloqueado("user@example.com", ahora=_T0) is False


def test_not_blocked_below_the_threshold() -> None:
    limiter = _limiter()
    for _ in range(4):
        limiter.registrar_intento_fallido("user@example.com", ahora=_T0)

    assert limiter.esta_bloqueado("user@example.com", ahora=_T0) is False


def test_blocked_once_it_hits_the_threshold() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.registrar_intento_fallido("user@example.com", ahora=_T0)

    assert limiter.esta_bloqueado("user@example.com", ahora=_T0) is True


def test_attempts_outside_the_window_do_not_count() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.registrar_intento_fallido("user@example.com", ahora=_T0)

    despues_de_la_ventana = _T0 + timedelta(minutes=16)

    assert limiter.esta_bloqueado("user@example.com", ahora=despues_de_la_ventana) is False


def test_limpiar_resets_the_key() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.registrar_intento_fallido("user@example.com", ahora=_T0)

    limiter.limpiar("user@example.com")

    assert limiter.esta_bloqueado("user@example.com", ahora=_T0) is False


def test_keys_are_independent() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.registrar_intento_fallido("blocked@example.com", ahora=_T0)

    assert limiter.esta_bloqueado("blocked@example.com", ahora=_T0) is True
    assert limiter.esta_bloqueado("other@example.com", ahora=_T0) is False
