from __future__ import annotations

import asyncio
import math
import re
import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

MonotonicClock = Callable[[], float]
RateLimitReason = Literal["allowed", "limit_exceeded", "capacity_exceeded"]

_SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RateLimitKey:
    """A non-secret rate-limit bucket identifier.

    The scope must be a constant operation category such as auth.login.ip.
    The subject digest must be a caller-produced lowercase SHA-256-sized digest.
    Callers should use HMAC-SHA-256 with a server-held key for low-entropy values
    such as IP addresses and email addresses. Raw identifiers must never be
    passed to or retained by the limiter.
    """

    scope: str
    subject_digest: str

    def __post_init__(self) -> None:
        if _SCOPE_PATTERN.fullmatch(self.scope) is None:
            raise ValueError(
                "Rate-limit scope must contain only lowercase letters, numbers, dots, "
                "underscores, and hyphens."
            )
        if _SHA256_HEX_PATTERN.fullmatch(self.subject_digest) is None:
            raise ValueError(
                "Rate-limit subjects must be supplied as a lowercase 64-character digest."
            )


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Result of one attempt to consume a rate-limit slot."""

    allowed: bool
    limit: int
    remaining: int
    retry_after: int | None
    reason: RateLimitReason


class SlidingWindowRateLimiter:
    """A bounded, concurrency-safe, process-local sliding-window limiter.

    The limiter stores only RateLimitKey values, so callers must derive scoped,
    non-reversible identifiers before calling acquire. Buckets and events are
    bounded by max_keys and limit respectively. When all retained key slots are
    active, an unseen key is rejected instead of evicting an active bucket and
    making key-churn bypass possible.

    This utility coordinates coroutines in one Python process only. A trusted
    edge limiter and/or distributed limiter remains required for multi-replica
    production deployments.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        max_keys: int = 10_000,
        prune_interval_seconds: float = 30.0,
        clock: MonotonicClock = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("Rate-limit capacity must be at least one.")
        if not math.isfinite(window_seconds) or window_seconds <= 0:
            raise ValueError("Rate-limit window must be a finite positive number.")
        if max_keys < 1:
            raise ValueError("Rate-limit key capacity must be at least one.")
        if not math.isfinite(prune_interval_seconds) or prune_interval_seconds <= 0:
            raise ValueError("Rate-limit prune interval must be a finite positive number.")

        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.prune_interval_seconds = prune_interval_seconds
        self._clock = clock
        self._buckets: OrderedDict[RateLimitKey, deque[float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._next_prune_at: float | None = None
        self._last_now: float | None = None

    async def acquire(self, key: RateLimitKey) -> RateLimitDecision:
        """Atomically consume one slot for the key or return a retry interval."""

        if not isinstance(key, RateLimitKey):
            raise TypeError("Rate limits require a validated RateLimitKey.")

        async with self._lock:
            now = self._read_clock()
            self._periodic_prune(now)

            bucket = self._buckets.get(key)
            if bucket is None:
                if len(self._buckets) >= self.max_keys:
                    self._prune_expired_buckets(now)
                if len(self._buckets) >= self.max_keys:
                    return RateLimitDecision(
                        allowed=False,
                        limit=self.limit,
                        remaining=0,
                        retry_after=self._capacity_retry_after(now),
                        reason="capacity_exceeded",
                    )
                bucket = deque()
                self._buckets[key] = bucket
            else:
                self._prune_bucket(bucket, now)
                if not bucket:
                    del self._buckets[key]
                    bucket = deque()
                    self._buckets[key] = bucket
                else:
                    self._buckets.move_to_end(key)

            if len(bucket) >= self.limit:
                return RateLimitDecision(
                    allowed=False,
                    limit=self.limit,
                    remaining=0,
                    retry_after=self._retry_after(bucket[0], now),
                    reason="limit_exceeded",
                )

            bucket.append(now)
            return RateLimitDecision(
                allowed=True,
                limit=self.limit,
                remaining=self.limit - len(bucket),
                retry_after=None,
                reason="allowed",
            )

    async def prune(self) -> int:
        """Remove expired key buckets and return the number removed."""

        async with self._lock:
            now = self._read_clock()
            removed = self._prune_expired_buckets(now)
            self._next_prune_at = now + self.prune_interval_seconds
            return removed

    async def retained_key_count(self) -> int:
        """Return the current number of retained digest buckets."""

        async with self._lock:
            return len(self._buckets)

    def _read_clock(self) -> float:
        now = self._clock()
        if not math.isfinite(now):
            raise RuntimeError("The monotonic rate-limit clock returned a non-finite value.")
        if self._last_now is not None and now < self._last_now:
            raise RuntimeError("The monotonic rate-limit clock moved backwards.")
        self._last_now = now
        return now

    def _periodic_prune(self, now: float) -> None:
        if self._next_prune_at is None or now >= self._next_prune_at:
            self._prune_expired_buckets(now)
            self._next_prune_at = now + self.prune_interval_seconds

    def _prune_expired_buckets(self, now: float) -> int:
        removed = 0
        for key, bucket in list(self._buckets.items()):
            self._prune_bucket(bucket, now)
            if not bucket:
                del self._buckets[key]
                removed += 1
        return removed

    def _prune_bucket(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _capacity_retry_after(self, now: float) -> int:
        earliest_bucket_expiry = min(
            bucket[-1] + self.window_seconds for bucket in self._buckets.values()
        )
        return self._ceil_retry_after(min(self.window_seconds, earliest_bucket_expiry - now))

    def _retry_after(self, oldest_event: float, now: float) -> int:
        return self._ceil_retry_after(
            min(self.window_seconds, oldest_event + self.window_seconds - now)
        )

    @staticmethod
    def _ceil_retry_after(seconds: float) -> int:
        return max(1, math.ceil(seconds))
