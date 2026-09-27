from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import patch

from hotel_management.application.dto import OutboxMessage
from hotel_management.infrastructure.messaging.webhook import (
    WebhookEventTransport,
    WebhookTransportSettings,
)
from hotel_management.infrastructure.messaging.n8n import N8nEventTransport


class FakeResponse:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class WebhookTransportTests(unittest.TestCase):
    def test_publish_posts_idempotent_event_envelope(self):
        transport = WebhookEventTransport(
            WebhookTransportSettings(
                "https://events.example.test/hotel",
                "secret-token",
                3,
            )
        )
        event = OutboxMessage(
            id=42,
            event_type="BookingCreated",
            occurred_at=datetime(2026, 9, 26, 10, 0, tzinfo=timezone.utc),
            payload={"booking_id": "booking-42"},
            attempts=2,
        )

        with patch(
            "hotel_management.infrastructure.messaging.webhook.urlopen",
            return_value=FakeResponse(),
        ) as urlopen:
            transport.publish(event)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://events.example.test/hotel")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(request.get_header("Idempotency-key"), "hotel-domain-event-42")
        self.assertEqual(json.loads(request.data), {
            "id": 42,
            "type": "BookingCreated",
            "occurred_at": "2026-09-26T10:00:00+00:00",
            "payload": {"booking_id": "booking-42"},
            "attempt": 2,
        })

    def test_settings_reject_non_http_urls(self):
        with self.assertRaises(ValueError):
            WebhookTransportSettings("file:///tmp/events", None, 10)

    def test_n8n_transport_uses_provider_specific_url_and_header_auth(self):
        event = OutboxMessage(
            id=7,
            event_type="BookingCreated",
            occurred_at=datetime(2026, 9, 26, 10, 0, tzinfo=timezone.utc),
            payload={"booking_id": "booking-7"},
            attempts=1,
        )
        environment = {
            "N8N_WEBHOOK_URL": "https://n8n.example.test/webhook/hotel",
            "N8N_WEBHOOK_TOKEN": "n8n-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            transport = N8nEventTransport.from_environment()
            with patch(
                "hotel_management.infrastructure.messaging.webhook.urlopen",
                return_value=FakeResponse(),
            ) as urlopen:
                transport.publish(event)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, environment["N8N_WEBHOOK_URL"])
        self.assertEqual(
            request.get_header("X-n8n-webhook-token"),
            "n8n-secret",
        )


if __name__ == "__main__":
    unittest.main()