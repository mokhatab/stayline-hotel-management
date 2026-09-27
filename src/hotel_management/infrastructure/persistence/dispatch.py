from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os

from hotel_management.application.use_cases.outbox import DispatchOutboxEvents
from hotel_management.infrastructure.configuration import PostgresSettings
from hotel_management.infrastructure.messaging.console import ConsoleEventTransport
from hotel_management.infrastructure.messaging.n8n import N8nEventTransport
from hotel_management.infrastructure.messaging.webhook import WebhookEventTransport
from hotel_management.infrastructure.persistence.postgres import (
    PostgresOutboxRepository,
    psycopg_connection_factory,
)
from hotel_management.infrastructure.persistence.in_memory import SystemClock


def build_dispatcher() -> DispatchOutboxEvents:
    settings = PostgresSettings.from_environment()
    connect = psycopg_connection_factory(settings.dsn)
    transport_name = os.environ.get("EVENT_TRANSPORT", "n8n").lower()
    if transport_name == "console":
        transport = ConsoleEventTransport()
    elif transport_name == "n8n":
        transport = N8nEventTransport.from_environment()
    elif transport_name == "webhook":
        transport = WebhookEventTransport.from_environment()
    else:
        raise RuntimeError(f"Unsupported EVENT_TRANSPORT: {transport_name}")
    return DispatchOutboxEvents(
        outbox=PostgresOutboxRepository(connect),
        transport=transport,
        clock=SystemClock(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch pending hotel domain events")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    result = build_dispatcher().execute(args.limit)
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == "__main__":
    main()