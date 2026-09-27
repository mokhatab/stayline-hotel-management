from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from hotel_management.application.dto import DispatchResult
from hotel_management.application.ports import Clock, EventTransport, OutboxRepository


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 5
    max_delay_seconds: int = 15 * 60
    lease_seconds: int = 5 * 60

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.base_delay_seconds < 1:
            raise ValueError("Retry policy values must be positive")

    def delay_for(self, attempts: int) -> timedelta:
        seconds = min(
            self.base_delay_seconds * (2 ** max(attempts - 1, 0)),
            self.max_delay_seconds,
        )
        return timedelta(seconds=seconds)


class DispatchOutboxEvents:
    """Claims, publishes, and records the outcome of pending outbox messages."""

    def __init__(
        self,
        outbox: OutboxRepository,
        transport: EventTransport,
        clock: Clock,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._outbox = outbox
        self._transport = transport
        self._clock = clock
        self._retry_policy = retry_policy or RetryPolicy()

    def execute(self, limit: int = 50) -> DispatchResult:
        if limit < 1:
            raise ValueError("Dispatch limit must be positive")
        started_at = self._clock.now()
        events = self._outbox.claim_pending(
            limit,
            started_at,
            started_at + timedelta(seconds=self._retry_policy.lease_seconds),
        )
        published = 0
        failed = 0
        permanently_failed = 0
        for event in events:
            try:
                self._transport.publish(event)
                self._outbox.mark_published(event.id, self._clock.now())
                published += 1
            except Exception as error:
                failed += 1
                permanent = event.attempts >= self._retry_policy.max_attempts
                next_attempt_at = (
                    None
                    if permanent
                    else self._clock.now() + self._retry_policy.delay_for(event.attempts)
                )
                self._outbox.mark_failed(
                    event.id,
                    str(error)[:2000],
                    self._clock.now(),
                    next_attempt_at,
                )
                permanently_failed += int(permanent)
        return DispatchResult(
            claimed=len(events),
            published=published,
            failed=failed,
            permanently_failed=permanently_failed,
        )