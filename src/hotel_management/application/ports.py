from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from hotel_management.application.dto import OutboxMessage
from hotel_management.domain.entities import Booking, Guest, Room
from hotel_management.domain.events import DomainEvent
from hotel_management.domain.value_objects import BookingId, DateRange, GuestId, RoomId


class GuestRepository(Protocol):
    def get(self, guest_id: GuestId) -> Guest | None: ...
    def save(self, guest: Guest) -> None: ...


class RoomRepository(Protocol):
    def get(self, room_id: RoomId) -> Room | None: ...
    def list(self) -> list[Room]: ...


class BookingRepository(Protocol):
    def get(self, booking_id: BookingId) -> Booking | None: ...
    def save(self, booking: Booking) -> None: ...
    def list_for_room(self, room_id: RoomId) -> list[Booking]: ...


class Clock(Protocol):
    def today(self) -> date: ...
    def now(self) -> datetime: ...


class EventPublisher(Protocol):
    def publish(self, events: list[DomainEvent]) -> None: ...


class OutboxRepository(Protocol):
    def claim_pending(
        self,
        limit: int,
        available_at: datetime,
        lease_until: datetime,
    ) -> list[OutboxMessage]: ...

    def mark_published(self, event_id: int, published_at: datetime) -> None: ...

    def mark_failed(
        self,
        event_id: int,
        error: str,
        failed_at: datetime,
        next_attempt_at: datetime | None,
    ) -> None: ...


class EventTransport(Protocol):
    def publish(self, event: OutboxMessage) -> None: ...


class BookingUnitOfWork(Protocol):
    """Transaction boundary owned by the application layer."""

    guests: GuestRepository
    rooms: RoomRepository
    bookings: BookingRepository
    events: EventPublisher

    def __enter__(self) -> "BookingUnitOfWork": ...
    def __exit__(self, exc_type, exc_value, traceback) -> None: ...


def room_is_available(
    room: Room,
    stay: DateRange,
    bookings: list[Booking],
) -> bool:
    if room.status.value != "available":
        return False
    return not any(
        booking.status.value in {"reserved", "checked_in"}
        and booking.stay.overlaps(stay)
        for booking in bookings
    )
