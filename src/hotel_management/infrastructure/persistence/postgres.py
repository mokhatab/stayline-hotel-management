from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import date
import json
from typing import Any
from uuid import UUID

from hotel_management.domain.entities import (
    Booking,
    BookingStatus,
    Guest,
    Room,
    RoomStatus,
    RoomType,
)
from hotel_management.domain.events import (
    BookingCheckedIn,
    BookingCheckedOut,
    BookingCreated,
    DomainEvent,
)
from hotel_management.domain.value_objects import (
    BookingId,
    DateRange,
    GuestId,
    Money,
    RoomId,
)
from hotel_management.application.dto import OutboxMessage


ConnectionFactory = Callable[[], Any]


class PostgresConnectionSession:
    """Keeps one psycopg connection open for a complete application transaction."""

    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection = None

    def __enter__(self) -> "PostgresConnectionSession":
        self._connection = self._connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._connection is None:
            return
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        if hasattr(self._connection, "close"):
            self._connection.close()
        self._connection = None

    @contextmanager
    def connection(self):
        if self._connection is None:
            raise RuntimeError("PostgreSQL session is not active")
        yield self._connection


@contextmanager
def _connection_scope(connections):
    if isinstance(connections, PostgresConnectionSession):
        with connections.connection() as connection:
            yield connection
    else:
        with connections() as connection:
            yield connection


def _commit_if_standalone(connections, connection) -> None:
    if not isinstance(connections, PostgresConnectionSession):
        connection.commit()


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _guest(row: tuple[Any, ...]) -> Guest:
    return Guest(
        id=GuestId(_uuid(row[0])),
        full_name=row[1],
        email=row[2],
        phone=row[3],
    )


def _room(row: tuple[Any, ...]) -> Room:
    return Room(
        id=RoomId(_uuid(row[0])),
        number=row[1],
        room_type=RoomType(row[2]),
        nightly_rate=Money(row[3], row[5]),
        capacity=row[4],
        status=RoomStatus(row[6]),
    )


def _booking(row: tuple[Any, ...]) -> Booking:
    return Booking(
        id=BookingId(_uuid(row[0])),
        guest_id=GuestId(_uuid(row[1])),
        room_id=RoomId(_uuid(row[2])),
        stay=DateRange(row[3], row[4]),
        guests=row[5],
        nightly_rate=Money(row[6], row[7]),
        status=BookingStatus(row[8]),
        created_at=row[9],
    )


class PostgresGuestRepository:
    """PostgreSQL implementation of the application GuestRepository port."""

    def __init__(self, connections: ConnectionFactory) -> None:
        self._connections = connections

    def get(self, guest_id: GuestId) -> Guest | None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, full_name, email, phone
                    FROM guests
                    WHERE id = %s
                    """,
                    (guest_id.value,),
                )
                row = cursor.fetchone()
        return _guest(row) if row else None

    def save(self, guest: Guest) -> None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO guests (id, full_name, email, phone)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone
                    """,
                    (guest.id.value, guest.full_name, guest.email, guest.phone),
                )
            _commit_if_standalone(self._connections, connection)


class PostgresRoomRepository:
    """PostgreSQL implementation of the application RoomRepository port."""

    _columns = "id, number, room_type, nightly_rate, capacity, currency, status"

    def __init__(self, connections: ConnectionFactory) -> None:
        self._connections = connections

    def get(self, room_id: RoomId) -> Room | None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {self._columns} FROM rooms WHERE id = %s",
                    (room_id.value,),
                )
                row = cursor.fetchone()
        return _room(row) if row else None

    def list(self) -> list[Room]:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT {self._columns} FROM rooms ORDER BY number")
                rows = cursor.fetchall()
        return [_room(row) for row in rows]


class PostgresBookingRepository:
    """PostgreSQL implementation of the application BookingRepository port."""

    _columns = (
        "id, guest_id, room_id, check_in, check_out, guests, "
        "nightly_rate, currency, status, created_at"
    )

    def __init__(self, connections: ConnectionFactory) -> None:
        self._connections = connections

    def get(self, booking_id: BookingId) -> Booking | None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {self._columns} FROM bookings WHERE id = %s",
                    (booking_id.value,),
                )
                row = cursor.fetchone()
        return _booking(row) if row else None

    def save(self, booking: Booking) -> None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO bookings (
                        id, guest_id, room_id, check_in, check_out, guests,
                        nightly_rate, currency, status, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        check_in = EXCLUDED.check_in,
                        check_out = EXCLUDED.check_out,
                        guests = EXCLUDED.guests
                    """,
                    (
                        booking.id.value,
                        booking.guest_id.value,
                        booking.room_id.value,
                        booking.stay.check_in,
                        booking.stay.check_out,
                        booking.guests,
                        booking.nightly_rate.amount,
                        booking.nightly_rate.currency,
                        booking.status.value,
                        booking.created_at,
                    ),
                )
            _commit_if_standalone(self._connections, connection)

    def list_for_room(self, room_id: RoomId) -> list[Booking]:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {self._columns}
                    FROM bookings
                    WHERE room_id = %s
                    ORDER BY check_in
                    """,
                    (room_id.value,),
                )
                rows = cursor.fetchall()
        return [_booking(row) for row in rows]


class PostgresEventPublisher:
    """Stores domain events in an outbox table for later delivery."""

    def __init__(self, connections: ConnectionFactory) -> None:
        self._connections = connections

    def publish(self, events: list[DomainEvent]) -> None:
        if not events:
            return
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                for event in events:
                    cursor.execute(
                        """
                        INSERT INTO domain_events (
                            event_type, occurred_at, payload, next_attempt_at
                        )
                        VALUES (%s, %s, %s::jsonb, %s)
                        """,
                        (
                            type(event).__name__,
                            event.occurred_at,
                            json.dumps(self._payload(event)),
                            event.occurred_at,
                        ),
                    )
            _commit_if_standalone(self._connections, connection)

    @staticmethod
    def _payload(event: DomainEvent) -> dict[str, str]:
        if isinstance(event, BookingCreated):
            return {
                "booking_id": str(event.booking_id),
                "guest_id": str(event.guest_id),
                "room_id": str(event.room_id),
                "check_in": event.check_in.isoformat(),
                "check_out": event.check_out.isoformat(),
            }
        if isinstance(event, BookingCheckedIn):
            return {
                "booking_id": str(event.booking_id),
                "guest_id": str(event.guest_id),
                "room_id": str(event.room_id),
                "checked_in_on": event.checked_in_on.isoformat(),
            }
        if isinstance(event, BookingCheckedOut):
            return {
                "booking_id": str(event.booking_id),
                "guest_id": str(event.guest_id),
                "room_id": str(event.room_id),
                "checked_out_on": event.checked_out_on.isoformat(),
            }
        return {}


class PostgresOutboxRepository:
    """Claims outbox rows safely across concurrent dispatcher processes."""

    _columns = (
        "id, event_type, occurred_at, payload, attempts"
    )

    def __init__(self, connections: ConnectionFactory) -> None:
        self._connections = connections

    def claim_pending(self, limit, available_at, lease_until) -> list[OutboxMessage]:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    WITH candidates AS (
                        SELECT id
                        FROM domain_events
                        WHERE published_at IS NULL
                          AND failed_at IS NULL
                          AND next_attempt_at <= %s
                          AND (locked_until IS NULL OR locked_until <= %s)
                        ORDER BY id
                        FOR UPDATE SKIP LOCKED
                        LIMIT %s
                    )
                    UPDATE domain_events AS event
                    SET attempts = event.attempts + 1,
                        locked_until = %s
                    FROM candidates
                    WHERE event.id = candidates.id
                    RETURNING {self._columns}
                    """,
                    (available_at, available_at, limit, lease_until),
                )
                rows = cursor.fetchall()
            _commit_if_standalone(self._connections, connection)
        return [
            OutboxMessage(
                id=row[0],
                event_type=row[1],
                occurred_at=row[2],
                payload=row[3],
                attempts=row[4],
            )
            for row in rows
        ]

    def mark_published(self, event_id, published_at) -> None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE domain_events
                    SET published_at = %s, locked_until = NULL
                    WHERE id = %s
                    """,
                    (published_at, event_id),
                )
            _commit_if_standalone(self._connections, connection)

    def mark_failed(
        self,
        event_id,
        error,
        failed_at,
        next_attempt_at,
    ) -> None:
        with _connection_scope(self._connections) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE domain_events
                    SET last_error = %s,
                        next_attempt_at = COALESCE(%s, next_attempt_at),
                        failed_at = CASE
                            WHEN %s IS NULL THEN %s
                            ELSE failed_at
                        END,
                        locked_until = NULL
                    WHERE id = %s
                    """,
                    (
                        error,
                        next_attempt_at,
                        next_attempt_at,
                        failed_at,
                        event_id,
                    ),
                )
            _commit_if_standalone(self._connections, connection)


class PostgresBookingUnitOfWork:
    """Atomic booking transaction over repositories and the event outbox."""

    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._session: PostgresConnectionSession | None = None

    def __enter__(self) -> "PostgresBookingUnitOfWork":
        self._session = PostgresConnectionSession(self._connect)
        self._session.__enter__()
        self.guests = PostgresGuestRepository(self._session)
        self.rooms = PostgresRoomRepository(self._session)
        self.bookings = PostgresBookingRepository(self._session)
        self.events = PostgresEventPublisher(self._session)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._session is not None:
            self._session.__exit__(exc_type, exc_value, traceback)
        self._session = None


def psycopg_connection_factory(dsn: str) -> ConnectionFactory:
    """Build the concrete external connection factory at the infrastructure edge."""
    import psycopg

    return lambda: psycopg.connect(dsn)
