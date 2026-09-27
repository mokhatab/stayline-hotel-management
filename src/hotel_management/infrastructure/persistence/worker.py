from __future__ import annotations

import os
import time

from hotel_management.infrastructure.persistence.dispatch import build_dispatcher


def run_forever(interval_seconds: int = 60, batch_size: int = 50) -> None:
    if interval_seconds < 1:
        raise ValueError("Worker interval must be at least one second")
    if batch_size < 1:
        raise ValueError("Worker batch size must be positive")

    dispatcher = build_dispatcher()
    print(
        "Outbox worker started "
        f"(interval={interval_seconds}s, batch_size={batch_size})"
    )
    while True:
        try:
            result = dispatcher.execute(batch_size)
            print(
                "Outbox cycle: "
                f"claimed={result.claimed} "
                f"published={result.published} "
                f"failed={result.failed} "
                f"permanently_failed={result.permanently_failed}"
            )
        except Exception as error:
            # A transient database or transport outage should not kill the worker.
            print(f"Outbox cycle failed: {error}")
        time.sleep(interval_seconds)


def main() -> None:
    interval_seconds = int(os.environ.get("OUTBOX_DISPATCH_INTERVAL_SECONDS", "60"))
    batch_size = int(os.environ.get("OUTBOX_BATCH_SIZE", "50"))
    run_forever(interval_seconds, batch_size)


if __name__ == "__main__":
    main()