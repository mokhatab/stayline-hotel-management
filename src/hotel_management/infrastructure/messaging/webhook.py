from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from hotel_management.application.dto import OutboxMessage


class WebhookTransportSettings:
    def __init__(
        self,
        url: str,
        token: str | None,
        timeout_seconds: int,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("EVENT_WEBHOOK_URL must be an HTTP or HTTPS URL")
        if timeout_seconds < 1:
            raise ValueError("EVENT_WEBHOOK_TIMEOUT_SECONDS must be positive")
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix

    @classmethod
    def from_environment(cls) -> "WebhookTransportSettings":
        url = os.environ.get("EVENT_WEBHOOK_URL")
        if not url:
            raise RuntimeError("EVENT_WEBHOOK_URL is required for webhook delivery")
        timeout = int(os.environ.get("EVENT_WEBHOOK_TIMEOUT_SECONDS", "10"))
        return cls(url, os.environ.get("EVENT_WEBHOOK_TOKEN"), timeout)


class WebhookEventTransport:
    """HTTP event adapter with idempotency and provider-agnostic payloads."""

    def __init__(self, settings: WebhookTransportSettings) -> None:
        self._settings = settings

    @classmethod
    def from_environment(cls) -> "WebhookEventTransport":
        return cls(WebhookTransportSettings.from_environment())

    def publish(self, event: OutboxMessage) -> None:
        payload = json.dumps(
            {
                "id": event.id,
                "type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "payload": event.payload,
                "attempt": event.attempts,
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "stayline-hotel-outbox/1.0",
            "X-Event-Id": str(event.id),
            "X-Event-Type": event.event_type,
            "Idempotency-Key": f"hotel-domain-event-{event.id}",
        }
        if self._settings.token:
            headers[self._settings.auth_header] = (
                f"{self._settings.auth_prefix}{self._settings.token}"
            )
        request = Request(
            self._settings.url,
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._settings.timeout_seconds) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(
                        f"Webhook returned unexpected status {response.status}"
                    )
        except HTTPError as error:
            body = error.read(512).decode("utf-8", errors="replace")
            raise RuntimeError(f"Webhook returned HTTP {error.code}: {body}") from error
        except URLError as error:
            raise RuntimeError(f"Webhook connection failed: {error.reason}") from error