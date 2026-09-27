#!/bin/sh
set -eu

PYTHONPATH=src python -m hotel_management &
WEB_PID=$!

PYTHONPATH=src python -m hotel_management.infrastructure.persistence.worker &
WORKER_PID=$!

cleanup() {
    kill "$WEB_PID" "$WORKER_PID" 2>/dev/null || true
    wait "$WEB_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

# Keep this process in the foreground for the deployment supervisor. If either
# child exits, terminate the other so the deployment restarts both together.
while kill -0 "$WEB_PID" 2>/dev/null && kill -0 "$WORKER_PID" 2>/dev/null; do
    sleep 5
done

exit 1