# Stayline Hotel Management

A small, runnable hotel-operations system built from the attached Clean
Architecture / Hexagonal Architecture prompt. The business core owns its
abstractions; the current in-memory persistence and HTTP server are replaceable
adapters.

## Run it

```bash
PYTHONPATH=src python -m hotel_management
```

Then open `http://127.0.0.1:8000`.

The project Run action is configured to use the same command. The starter data
contains rooms 101, 202, and 303. Restarting the app resets in-memory data.

## Desktop app

The source archive includes a desktop launcher under `desktop/`. It starts the
same local application and opens it in a native `pywebview` window when
available, with a browser fallback:

```bash
sh desktop/setup-desktop.sh
.venv/bin/python desktop/run_desktop.py
```

On Windows PowerShell, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\setup-desktop.ps1
.\.venv\Scripts\python.exe desktop\run_desktop.py
```

See `desktop/README.md` for platform notes and the Linux launcher template.

## PostgreSQL adapter

The PostgreSQL adapter implements the same application ports as the in-memory
adapter. The domain entities and use cases do not import `psycopg`, SQL, or
database-specific types.

1. Set `DATABASE_URL` (or `HOTEL_DATABASE_URL`) in the environment.
2. Apply the schema and seed the three starter rooms:

   ```bash
   HOTEL_STORAGE=postgres PYTHONPATH=src python -m hotel_management.infrastructure.persistence.migrate
   ```

3. Start the application against PostgreSQL:

   ```bash
   HOTEL_STORAGE=postgres PYTHONPATH=src python -m hotel_management
   ```

The default remains in-memory so the app can still run locally without a
database. The migration and repositories live under
`src/hotel_management/infrastructure/persistence/`.

Booking creation uses a core-owned unit-of-work port. With PostgreSQL enabled,
the booking row and its outbox event share one connection and commit together;
any exception rolls both back.

## Outbox dispatcher

Pending domain events can be dispatched in a worker process:

```bash
HOTEL_STORAGE=postgres \
DATABASE_URL="postgresql://user:password@host:5432/hotel" \
N8N_WEBHOOK_URL="https://your-n8n.example.com/webhook/stayline-hotel-events" \
N8N_WEBHOOK_TOKEN="set-this-in-deployment-secrets" \
PYTHONPATH=src \
python -m hotel_management.infrastructure.persistence.dispatch --limit 50
```

The dispatcher uses row locking and a lease so multiple workers can run safely.
Failed deliveries record the error and attempt count, retry with exponential
backoff, and become permanently failed after five attempts. Production delivery
uses n8n's production Webhook URL. `N8N_WEBHOOK_TOKEN` is optional. Each request
includes `X-Event-Id`, `X-Event-Type`, and an `Idempotency-Key` header so the
receiving provider can deduplicate at-least-once deliveries. Set
`N8N_WEBHOOK_AUTH_HEADER` if the n8n Webhook node uses a different header name.
Set `EVENT_TRANSPORT=console` only for explicit local testing; production
defaults to n8n.

An importable workflow is included at
`n8n/stayline-hotel-events-router.workflow.json`. Import it into n8n, set the
Webhook node to use its production URL, publish the workflow, and configure the
same production URL as `N8N_WEBHOOK_URL`. It routes `BookingCreated`,
`BookingCheckedIn`, and `BookingCheckedOut` to separate branches and sends
unknown event types to an explicit unsupported branch.

For a continuously running worker, use the project worker entrypoint:

```bash
HOTEL_STORAGE=postgres \
DATABASE_URL="postgresql://user:password@host:5432/hotel" \
N8N_WEBHOOK_URL="https://your-n8n.example.com/webhook/stayline-hotel-events" \
N8N_WEBHOOK_TOKEN="set-this-in-deployment-secrets" \
OUTBOX_DISPATCH_INTERVAL_SECONDS=60 \
OUTBOX_BATCH_SIZE=50 \
PYTHONPATH=src \
python -m hotel_management.infrastructure.persistence.worker
```

Run this as a separate background process from the web server. The worker
continues after a transient database or transport error and retries on its next
poll.

## Reserved VM deployment

The project includes `scripts/run-production.sh`, which starts the web server
and outbox worker as supervised sibling processes. The `.replit` deployment
command uses this script. Configure `DATABASE_URL`, `HOTEL_STORAGE=postgres`,
`N8N_WEBHOOK_URL`, and optionally `N8N_WEBHOOK_TOKEN`,
and the worker settings as deployment environment variables.

This two-process configuration is intended for a Reserved VM deployment. For
Autoscale, keep the web app as one deployment and deploy the worker as a
separate worker project or service, because Autoscale is designed around one
primary service per deployment.

## API slice

Search room availability:

```bash
curl 'http://127.0.0.1:8000/api/rooms?check_in=2026-10-01&check_out=2026-10-03&guests=2'
```

Register a guest:

```bash
curl -X POST http://127.0.0.1:8000/api/guests \
  -H 'Content-Type: application/json' \
  -d '{"full_name":"Grace Hopper","email":"grace@example.com"}'
```

Create a booking with the returned guest id and an available room id:

```bash
curl -X POST http://127.0.0.1:8000/api/bookings \
  -H 'Content-Type: application/json' \
  -d '{"guest_id":"<guest-id>","room_id":"<room-id>","check_in":"2026-10-01","check_out":"2026-10-03","guests":2}'
```

Stay lifecycle:

```text
POST /api/bookings/<booking-id>/check-in
POST /api/bookings/<booking-id>/check-out
```

## Verify the architecture

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The tests cover domain invariants, application orchestration with ports, and
static dependency rules preventing the core from importing infrastructure or
HTTP concerns. See [`docs/architecture.md`](docs/architecture.md) for the
domain model, use-case catalog, adapter catalog, and architecture audit.