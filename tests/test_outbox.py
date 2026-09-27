from datetime import datetime, timedelta, timezone
import unittest

from hotel_management.application.dto import OutboxMessage
from hotel_management.application.use_cases.outbox import (
    DispatchOutboxEvents,
    RetryPolicy,
)


class FixedClock:
    def __init__(self):
        self.current = datetime(2026, 9, 26, 10, 0, tzinfo=timezone.utc)

    def today(self):
        return self.current.date()

    def now(self):
        return self.current


class FakeOutbox:
    def __init__(self, events):
        self.events = events
        self.published = []
        self.failures = []

    def claim_pending(self, limit, available_at, lease_until):
        return self.events[:limit]

    def mark_published(self, event_id, published_at):
        self.published.append((event_id, published_at))

    def mark_failed(self, event_id, error, failed_at, next_attempt_at):
        self.failures.append((event_id, error, failed_at, next_attempt_at))


class FakeTransport:
    def __init__(self, failures=0):
        self.failures = failures
        self.published = []

    def publish(self, event):
        if len(self.published) < self.failures:
            raise RuntimeError("downstream unavailable")
        self.published.append(event.id)


def event(event_id=1, attempts=1):
    return OutboxMessage(
        id=event_id,
        event_type="BookingCreated",
        occurred_at=datetime(2026, 9, 26, 9, 59, tzinfo=timezone.utc),
        payload={"booking_id": "booking-1"},
        attempts=attempts,
    )


class OutboxTests(unittest.TestCase):
    def test_successful_event_is_marked_published(self):
        outbox = FakeOutbox([event()])
        dispatcher = DispatchOutboxEvents(outbox, FakeTransport(), FixedClock())

        result = dispatcher.execute()

        self.assertEqual(result.published, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(outbox.published[0][0], 1)

    def test_failed_event_is_scheduled_with_exponential_backoff(self):
        outbox = FakeOutbox([event(attempts=2)])
        dispatcher = DispatchOutboxEvents(
            outbox,
            FakeTransport(failures=1),
            FixedClock(),
            RetryPolicy(base_delay_seconds=5),
        )

        result = dispatcher.execute()

        self.assertEqual(result.failed, 1)
        self.assertEqual(result.permanently_failed, 0)
        self.assertEqual(
            outbox.failures[0][3],
            datetime(2026, 9, 26, 10, 0, 10, tzinfo=timezone.utc),
        )

    def test_max_attempts_marks_event_permanently_failed(self):
        outbox = FakeOutbox([event(attempts=5)])
        dispatcher = DispatchOutboxEvents(
            outbox,
            FakeTransport(failures=1),
            FixedClock(),
            RetryPolicy(max_attempts=5),
        )

        result = dispatcher.execute()

        self.assertEqual(result.permanently_failed, 1)
        self.assertIsNone(outbox.failures[0][3])

    def test_retry_policy_caps_backoff(self):
        policy = RetryPolicy(base_delay_seconds=5, max_delay_seconds=20)

        self.assertEqual(policy.delay_for(1), timedelta(seconds=5))
        self.assertEqual(policy.delay_for(5), timedelta(seconds=20))


if __name__ == "__main__":
    unittest.main()