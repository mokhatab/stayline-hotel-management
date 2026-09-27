import os
import unittest
from unittest.mock import patch

from hotel_management.infrastructure.persistence.dispatch import build_dispatcher


class DispatchCompositionTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://example/hotel",
        },
        clear=True,
    )
    @patch(
        "hotel_management.infrastructure.persistence.dispatch.N8nEventTransport"
    )
    @patch(
        "hotel_management.infrastructure.persistence.dispatch.psycopg_connection_factory"
    )
    def test_production_dispatch_defaults_to_n8n(
        self,
        connection_factory,
        n8n_transport,
    ):
        connection_factory.return_value = lambda: None
        transport = object()
        n8n_transport.from_environment.return_value = transport

        dispatcher = build_dispatcher()

        n8n_transport.from_environment.assert_called_once_with()
        self.assertIs(dispatcher._transport, transport)

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://example/hotel",
            "EVENT_TRANSPORT": "webhook",
            "WEBHOOK_URL": "https://events.example.test/hotel",
        },
        clear=True,
    )
    @patch(
        "hotel_management.infrastructure.persistence.dispatch.WebhookEventTransport"
    )
    @patch(
        "hotel_management.infrastructure.persistence.dispatch.psycopg_connection_factory"
    )
    def test_generic_webhook_remains_an_explicit_transport(
        self,
        connection_factory,
        webhook_transport,
    ):
        connection_factory.return_value = lambda: None
        transport = object()
        webhook_transport.from_environment.return_value = transport

        dispatcher = build_dispatcher()

        webhook_transport.from_environment.assert_called_once_with()
        self.assertIs(dispatcher._transport, transport)


if __name__ == "__main__":
    unittest.main()