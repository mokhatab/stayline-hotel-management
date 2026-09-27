# Stayline Hotel Management — Architecture

This implementation follows the attached Clean Architecture / Hexagonal Architecture prompt.
It is deliberately small enough to run immediately while keeping the business core independent
of persistence and delivery technologies.

## Architecture diagram

```text
                         external clients
                               │
                               ▼
                  interfaces/http (adapter)
                               │
                               ▼
                    application use cases
                         │       │
                         ▼       ▼
                 domain model   application ports
                                     ▲
                                     │ implements
                         infrastructure adapters
                         (in-memory today, SQL later)
```

Dependency direction is inward:

```text
interfaces ───────► application ───────► domain
infrastructure ──► application ports ──► domain
composition ──────► all concrete pieces (wiring only)
```

## Layer responsibility matrix

| Layer | Owns | Must not know |
|---|---|---|
| Domain | Guest, Room, Booking, value objects, invariants, events | HTTP, JSON, storage, frameworks |
| Application | Commands, DTOs, use cases, ports, orchestration | SQL, repository implementations, HTTP |
| Infrastructure | Repository and event-port implementations, seed data | UI concerns |
| Interfaces | HTTP translation, status codes, JSON, dashboard | Business rules and persistence |
| Composition | Dependency injection and startup | None; it is the wiring boundary |

## Domain model and invariants

* A room has a capacity, room type, nightly rate, and operational status.
* A guest must have a name and an email.
* A booking has a guest, room, half-open date range `[check_in, check_out)`,
  guest count, rate snapshot, and lifecycle status.
* Check-out must be after check-in.
* Guest count must fit room capacity.
* A room cannot have overlapping reserved or checked-in bookings.
* A booking cannot be checked in before arrival or after the stay ends.
* Only checked-in bookings can be checked out.

## Use-case catalog

| Use case | Input | Output | Ports |
|---|---|---|---|
| RegisterGuest | name, email, phone | Guest | GuestRepository |
| CreateBooking | guest, room, dates, guest count | BookingView | GuestRepository, RoomRepository, BookingRepository, EventPublisher |
| ListAvailableRooms | dates, guest count | RoomView list | RoomRepository, BookingRepository |
| CheckInGuest | booking id | BookingView | BookingRepository, Clock |
| CheckOutGuest | booking id | BookingView | BookingRepository, Clock |

The HTTP adapter exposes the first three routes today:

* `GET /api/rooms?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD&guests=2`
* `POST /api/guests`
* `POST /api/bookings`
* `POST /api/bookings/<booking-id>/check-in`
* `POST /api/bookings/<booking-id>/check-out`

## Port and adapter catalog

| Core port | Current adapter | Replacement examples |
|---|---|---|
| GuestRepository | InMemoryGuestRepository | PostgresGuestRepository |
| RoomRepository | InMemoryRoomRepository | PostgresRoomRepository |
| BookingRepository | InMemoryBookingRepository | PostgresBookingRepository |
| EventPublisher | InMemoryEventPublisher | PostgresEventPublisher (outbox) |
| BookingUnitOfWork | InMemoryBookingUnitOfWork | PostgresBookingUnitOfWork |
| OutboxRepository | InMemoryOutboxRepository | PostgresOutboxRepository |
| EventTransport | Test fake | N8nEventTransport |
| Clock | SystemClock | FixedClock in tests |

## Composition strategy

`composition/bootstrap.py` is the composition root. It creates concrete adapters,
injects them into use cases, and exposes a controller. No use case instantiates an
adapter. Replacing in-memory storage means changing this wiring and adding an adapter,
not changing domain or application code.

## PostgreSQL persistence

Set `HOTEL_STORAGE=postgres` and `DATABASE_URL` to select the adapter. The schema
is in `infrastructure/persistence/schema.sql`, and the migration entrypoint is
`python -m hotel_management.infrastructure.persistence.migrate`. PostgreSQL
details, `psycopg`, SQL, and JSONB outbox storage are confined to infrastructure.

The outbox stores domain events for downstream delivery. The current
`BookingUnitOfWork` makes booking persistence and outbox insertion atomic, and
the dispatcher publishes unprocessed events separately; domain entities remain
unchanged.

`CreateBooking` depends on the application-owned `BookingUnitOfWork` port. The
in-memory implementation snapshots state and restores it on failure. The
PostgreSQL implementation opens one connection, injects transaction-bound
repositories into the use case, commits on successful scope exit, and rolls
back on exceptions.

`DispatchOutboxEvents` is a separate application use case. It claims pending
messages through `OutboxRepository`, sends them through `EventTransport`, and
records success or failure. PostgreSQL uses `FOR UPDATE SKIP LOCKED`, a lease,
attempt count, last error, retry timestamp, and permanent-failure timestamp.
The default retry policy is five attempts with capped exponential backoff.

Production delivery uses `N8nEventTransport`, which targets an n8n production
Webhook URL and sends JSON over HTTP with an idempotency key, event headers,
optional header-token authentication, and timeout/error propagation. A Kafka,
SNS, or another provider-specific adapter can replace it without changing the
dispatcher use case.

The importable workflow at
`n8n/stayline-hotel-events-router.workflow.json` switches on the event `type`
and routes `BookingCreated`, `BookingCheckedIn`, and `BookingCheckedOut`
separately. Unknown event types are retained on an unsupported branch for
observability instead of being silently dropped.

`infrastructure/persistence/worker.py` runs this use case continuously as a
separate process. Its poll interval and batch size are configured through
`OUTBOX_DISPATCH_INTERVAL_SECONDS` and `OUTBOX_BATCH_SIZE`. This keeps the web
server independent from background delivery.

For Reserved VM deployment, `scripts/run-production.sh` supervises the web
server and worker as sibling processes and stops the other process if either
one exits. Autoscale deployments should use a separate worker deployment
instead of this two-process command.

## Testing and enforcement strategy

* `tests/test_domain.py` proves business invariants without infrastructure.
* `tests/test_application.py` proves orchestration using in-memory fakes.
* `tests/test_architecture.py` parses imports and rejects core-to-infrastructure or
  core-to-HTTP dependencies.
* `tests/test_postgres_adapter.py` tests adapter mapping and SQL boundaries without
  requiring a running database; live integration tests should be added when a
  PostgreSQL environment is available.
* Transaction tests prove both in-memory rollback and PostgreSQL connection
  commit/rollback semantics.
* `tests/test_outbox.py` proves successful dispatch, backoff, maximum-attempt
  failure, and backoff capping without a database or network.
* End-to-end tests should exercise the HTTP server once the API surface stabilizes.

Run:

```bash
python -m unittest discover -s tests -v
python -m hotel_management
```

The app runs at `http://127.0.0.1:8000` and defaults to in-memory data. Set
`HOTEL_STORAGE=postgres` and `DATABASE_URL` to use persistent storage instead.

## Architecture audit

1. Domain without a database: **Yes**.
2. Use cases without a database: **Yes**.
3. In-memory application: **Yes**.
4. Database replaceable without business changes: **Yes, through ports**.
5. UI/API replaceable without business changes: **Yes, through use cases**.
6. Payment provider replaceable: **Not yet applicable**; payments are outside this slice.
7. Infrastructure mockable: **Yes, ports are protocols**.
8. External dependencies represented by interfaces: **Yes for this slice**.
9. Controllers free of business logic: **Yes; they translate and invoke**.
10. Rules in domain/application: **Yes**.
11. Dependency direction inward: **Yes**.
12. Core free of framework/ORM imports: **Yes**.
13. Violations automatically detected: **Yes, by architecture tests**.
