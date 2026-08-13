from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from insightforge.core.rate_limiting import RateLimitKey, SlidingWindowRateLimiter


@dataclass
class FakeMonotonicClock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def key(index: int, *, scope: str = "auth.login.ip") -> RateLimitKey:
    return RateLimitKey(scope=scope, subject_digest=f"{index:064x}")


def test_keys_require_constant_scopes_and_prehashed_subjects() -> None:
    valid = key(1)

    assert valid.scope == "auth.login.ip"
    assert valid.subject_digest == f"{1:064x}"
    with pytest.raises(ValueError, match="lowercase 64-character digest"):
        RateLimitKey(scope="auth.login.email", subject_digest="owner@example.com")
    with pytest.raises(ValueError, match="scope"):
        RateLimitKey(scope="owner@example.com", subject_digest=f"{1:064x}")


@pytest.mark.asyncio
async def test_sliding_window_returns_retry_after_and_recovers_at_boundary() -> None:
    clock = FakeMonotonicClock()
    limiter = SlidingWindowRateLimiter(
        limit=2,
        window_seconds=10,
        max_keys=10,
        prune_interval_seconds=2,
        clock=clock,
    )

    first = await limiter.acquire(key(1))
    second = await limiter.acquire(key(1))
    rejected = await limiter.acquire(key(1))

    assert first.allowed and first.remaining == 1
    assert second.allowed and second.remaining == 0
    assert not rejected.allowed
    assert rejected.reason == "limit_exceeded"
    assert rejected.retry_after == 10

    clock.advance(4.2)
    still_rejected = await limiter.acquire(key(1))
    assert still_rejected.retry_after == 6

    clock.advance(5.8)
    recovered = await limiter.acquire(key(1))
    assert recovered.allowed
    assert recovered.remaining == 1
    assert recovered.retry_after is None


@pytest.mark.asyncio
async def test_concurrent_attempts_cannot_oversubscribe_one_bucket() -> None:
    limiter = SlidingWindowRateLimiter(
        limit=5,
        window_seconds=60,
        max_keys=10,
        clock=FakeMonotonicClock(),
    )

    decisions = await asyncio.gather(*(limiter.acquire(key(1)) for _ in range(50)))

    assert sum(decision.allowed for decision in decisions) == 5
    assert all(
        decision.reason == "limit_exceeded" for decision in decisions if not decision.allowed
    )


@pytest.mark.asyncio
async def test_key_capacity_fails_closed_and_expired_buckets_are_pruned() -> None:
    clock = FakeMonotonicClock()
    limiter = SlidingWindowRateLimiter(
        limit=2,
        window_seconds=5,
        max_keys=2,
        prune_interval_seconds=1,
        clock=clock,
    )

    assert (await limiter.acquire(key(1))).allowed
    assert (await limiter.acquire(key(2))).allowed

    capacity_rejection = await limiter.acquire(key(3))
    assert not capacity_rejection.allowed
    assert capacity_rejection.reason == "capacity_exceeded"
    assert capacity_rejection.retry_after == 5
    assert await limiter.retained_key_count() == 2

    for index in range(4, 50):
        assert not (await limiter.acquire(key(index))).allowed
    assert await limiter.retained_key_count() == 2

    clock.advance(5)
    assert (await limiter.acquire(key(3))).allowed
    assert await limiter.retained_key_count() == 1


@pytest.mark.asyncio
async def test_explicit_prune_and_clock_validation_are_deterministic() -> None:
    clock = FakeMonotonicClock()
    limiter = SlidingWindowRateLimiter(
        limit=1,
        window_seconds=3,
        max_keys=3,
        clock=clock,
    )

    await limiter.acquire(key(1))
    await limiter.acquire(key(2))
    clock.advance(3)

    assert await limiter.prune() == 2
    assert await limiter.retained_key_count() == 0

    clock.advance(-1)
    with pytest.raises(RuntimeError, match="moved backwards"):
        await limiter.acquire(key(3))


@pytest.mark.asyncio
async def test_acquire_rejects_unvalidated_raw_keys() -> None:
    limiter = SlidingWindowRateLimiter(
        limit=1,
        window_seconds=10,
        max_keys=1,
        clock=FakeMonotonicClock(),
    )

    with pytest.raises(TypeError, match="validated RateLimitKey"):
        await limiter.acquire("auth.login.ip:203.0.113.10")  # type: ignore[arg-type]
    assert await limiter.retained_key_count() == 0
