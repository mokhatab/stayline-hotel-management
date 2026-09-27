from __future__ import annotations

import os

from hotel_management.infrastructure.messaging.webhook import (
    WebhookEventTransport,
    WebhookTransportSettings,
)


class N8nEventTransport(WebhookEventTransport):
    """n8n Webhook-node adapter using its production webhook URL."""

    @classmethod
    def from_environment(cls) -> "N8nEventTransport":
        url = os.environ.get("N8N_WEBHOOK_URL")
        if not url:
            raise RuntimeError("N8N_WEBHOOK_URL is required for n8n delivery")
        settings = WebhookTransportSettings(
            url=url,
            token=os.environ.get("N8N_WEBHOOK_TOKEN"),
            timeout_seconds=int(
                os.environ.get("N8N_WEBHOOK_TIMEOUT_SECONDS", "10")
            ),
            auth_header=os.environ.get(
                "N8N_WEBHOOK_AUTH_HEADER",
                "X-N8N-Webhook-Token",
            ),
            auth_prefix="",
        )
        return cls(settings)