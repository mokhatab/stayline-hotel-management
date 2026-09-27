from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from hotel_management.domain.entities import Booking, Room


@dataclass(frozen=True)
class CreateGuestCommand:
    full_name: str
    email: str
    phone: str | None = None


@dataclass(frozen=True)
class CreateBookingCommand:
    guest_id: str
    room_id: str
    check_in: str
    check_out: str
    guests: int


@dataclass(frozen=True)
class BookingView:
    id: str
    guest_id: str
    room_id: str
    check_in: date
    check_out: date
    nights: int
    guests: int
    status: str
    total: Decimal
    currency: str

    @classmethod
    def from_entity(cls, booking: Booking) -> "BookingView":
        return cls(
            id=str(booking.id),
            guest_id=str(booking.guest_id),
            room_id=str(booking.room_id),
            check_in=booking.stay.check_in,
            check_out=booking.stay.check_out,
            nights=booking.stay.nights,
            guests=booking.guests,
            status=booking.status.value,
            total=booking.total.amount,
            currency=booking.total.currency,
        )


@dataclass(frozen=True)
class RoomView:
    id: str
    number: str
    room_type: str
    capacity: int
    nightly_rate: Decimal
    currency: str
    status: str
    available: bool

    @classmethod
    def from_entity(cls, room: Room, available: bool) -> "RoomView":
        return cls(
            id=str(room.id),
            number=room.number,
            room_type=room.room_type.value,
            capacity=room.capacity,
            nightly_rate=room.nightly_rate.amount,
            currency=room.nightly_rate.currency,
            status=room.status.value,
            available=available,
        )


@dataclass(frozen=True)
class OutboxMessage:
    id: int
    event_type: str
    occurred_at: datetime
    payload: dict
    attempts: int


@dataclass(frozen=True)
class DispatchResult:
    claimed: int
    published: int
    failed: int
    permanently_failed: int
