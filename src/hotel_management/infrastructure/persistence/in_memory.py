from __future__ import annotations

from datetime import date, datetime, timezone
from copy import deepcopy
from dataclasses import replace

from hotel_management.domain.entities import Booking, Guest, Room
from hotel_management.domain.events import DomainEvent
from hotel_management.domain.value_objects import BookingId, GuestId, RoomId


class InMemoryGuestRepository:
    def __init__(self) -> None:
        self._items: dict[GuestId, Guest] = {}

    def get(self, guest_id: GuestId) -> Guest | None:
        return self._items.get(guest_id)

    def save(self, guest: Guest) -> None:
        self._items[guest.id] = guest


class InMemoryRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self._items = {room.id: room for room in rooms or []}

    def get(self, room_id: RoomId) -> Room | None:
        return self._items.get(room_id)

    def list(self) -> list[Room]:
        return list(self._items.values())

    def save(self, room: Room) -> None:
        self._items[room.id] = room


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._items: dict[BookingId, Booking] = {}

    def get(self, booking_id: BookingId) -> Booking | None:
        return self._items.get(booking_id)

    def save(self, booking: Booking) -> None:
        self._items[booking.id] = booking

    def list_for_room(self, room_id: RoomId) -> list[Booking]:
        return [booking for booking in self._items.values() if booking.room_id == room_id]

    def list(self) -> list[Booking]:
        return list(self._items.values())


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, events: list[DomainEvent]) -> None:
        self.published.extend(events)


class InMemoryOutboxRepository:
    def __init__(self) -> None:
        self.messages = []
        self.published: dict[int, datetime] = {}
        self.failures: list[tuple[int, str, datetime | None]] = []
        self._attempts: dict[int, int] = {}
        self._next_attempt_at: dict[int, datetime] = {}
        self._failed: set[int] = set()

    def add(self, message) -> None:
        self.messages.append(message)

    def claim_pending(self, limit, available_at, lease_until):
        pending = [
            replace(
                message,
                attempts=self._attempts.get(message.id, message.attempts) + 1,
            )
            for message in self.messages
            if message.id not in self.published
            and message.id not in self._failed
            and self._next_attempt_at.get(message.id, available_at) <= available_at
        ]
        for message in pending[:limit]:
            self._attempts[message.id] = message.attempts
        return pending[:limit]

    def mark_published(self, event_id, published_at):
        self.published[event_id] = published_at

    def mark_failed(self, event_id, error, failed_at, next_attempt_at):
        self.failures.append((event_id, error, next_attempt_at))
        if next_attempt_at is None:
            self._failed.add(event_id)
        else:
            self._next_attempt_at[event_id] = next_attempt_at


class InMemoryBookingUnitOfWork:
    """Transactional fake with rollback semantics for application tests."""

    def __init__(
        self,
        guests: InMemoryGuestRepository,
        rooms: InMemoryRoomRepository,
        bookings: InMemoryBookingRepository,
        events: InMemoryEventPublisher,
    ) -> None:
        self.guests = guests
        self.rooms = rooms
        self.bookings = bookings
        self.events = events
        self._snapshot = None

    def __enter__(self) -> "InMemoryBookingUnitOfWork":
        self._snapshot = (
            deepcopy(self.guests._items),
            deepcopy(self.rooms._items),
            deepcopy(self.bookings._items),
            list(self.events.published),
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None and self._snapshot is not None:
            (
                self.guests._items,
                self.rooms._items,
                self.bookings._items,
                self.events.published,
            ) = self._snapshot
        self._snapshot = None


class SystemClock:
    def today(self) -> date:
        return date.today()

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
