import json

from hotel_management.application.dto import OutboxMessage


class ConsoleEventTransport:
    """Safe local transport; replace with Kafka, webhook, or another provider."""

    def publish(self, event: OutboxMessage) -> None:
        print(
            json.dumps(
                {
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at.isoformat(),
                    "payload": event.payload,
                },
                sort_keys=True,
            )
        )