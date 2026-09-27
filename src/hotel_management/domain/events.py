from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from .value_objects import BookingId, GuestId, RoomId


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime

    @classmethod
    def now(cls):
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BookingCreated(DomainEvent):
    booking_id: BookingId
    guest_id: GuestId
    room_id: RoomId
    check_in: date
    check_out: date


@dataclass(frozen=True)
class BookingCheckedIn(DomainEvent):
    booking_id: BookingId
    guest_id: GuestId
    room_id: RoomId
    checked_in_on: date


@dataclass(frozen=True)
class BookingCheckedOut(DomainEvent):
    booking_id: BookingId
    guest_id: GuestId
    room_id: RoomId
    checked_out_on: date
