"""Pure-function timeout/retry/budget/circuit helpers for the LLM port.

No sleeping and no network here: callers decide when to apply backoff. Every
helper is deterministic given its inputs so tests never flake.
"""

from __future__ import annotations

import random

from .errors import LLMProviderError


def backoff_sequence(*, max_attempts: int, base_ms: int, cap_ms: int) -> tuple[int, ...]:
    """Return deterministic full-jitter backoff delays for `max_attempts`.

    The first delay is zero (the first attempt is immediate); later attempts
    draw from a fixed seed so repeated calls produce identical sequences.
    Values never exceed `cap_ms`.
    """

    rng = random.Random(0x4C4D)  # deterministic "LLM" seed
    delays: list[int] = []
    for attempt in range(max_attempts):
        if attempt == 0:
            delays.append(0)
            continue
        upper = min(cap_ms, base_ms * (2 ** (attempt - 1)))
        delays.append(rng.randint(0, max(1, upper)))
    return tuple(delays)


class AttemptBudget:
    """Tracks attempts against a budget and fails closed when exhausted."""

    def __init__(self, *, max_attempts: int, max_latency_ms: int | None = None) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if max_latency_ms is not None and max_latency_ms < 1:
            raise ValueError("max_latency_ms must be >= 1")
        self._max_attempts = max_attempts
        self._max_latency_ms = max_latency_ms
        self._used = 0

    def remaining(self) -> int:
        return self._max_attempts - self._used

    def record_attempt(self) -> None:
        if self._used >= self._max_attempts:
            raise LLMProviderError(
                "budget_exceeded",
                details={"rule": "attempt_budget_exhausted", "max_attempts": self._max_attempts},
            )
        self._used += 1


class CircuitBreaker:
    """Closed/open/half-open state machine keyed by provider+endpoint+model.

    Auth/balance failures must open the breaker immediately (no retries);
    half-open only lets a probe through, and one success closes it again.
    Time is simulated via `advance_clock` so tests are deterministic.
    """

    def __init__(self, *, failure_threshold: int, open_seconds: float) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if open_seconds <= 0:
            raise ValueError("open_seconds must be positive")
        self._failure_threshold = failure_threshold
        self._open_seconds = open_seconds
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._now = 0.0

    def advance_clock(self, seconds: float) -> None:
        self._now += seconds

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._opened_at = self._now

    def open_immediately(self) -> None:
        """Open without waiting for the threshold (auth/balance failures)."""

        self._opened_at = self._now

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def allow_request(self) -> bool:
        """True in closed state and for a half-open probe; False while open."""

        return self._opened_at is None or self._now - self._opened_at >= self._open_seconds
