from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from .events import BookingCheckedIn, BookingCheckedOut, BookingCreated, DomainEvent
from .exceptions import InvalidBookingStateError, ValidationError
from .value_objects import BookingId, DateRange, GuestId, Money, RoomId


class RoomStatus(str, Enum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"


class RoomType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"


@dataclass
class Guest:
    id: GuestId
    full_name: str
    email: str
    phone: str | None = None

    def __post_init__(self) -> None:
        self.full_name = self.full_name.strip()
        self.email = self.email.strip().lower()
        if len(self.full_name) < 2:
            raise ValidationError("Guest name must contain at least two characters")
        if "@" not in self.email or self.email.startswith("@"):
            raise ValidationError("Guest email is invalid")


@dataclass
class Room:
    id: RoomId
    number: str
    room_type: RoomType
    nightly_rate: Money
    capacity: int
    status: RoomStatus = RoomStatus.AVAILABLE

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise ValidationError("Room number is required")
        if self.capacity < 1:
            raise ValidationError("Room capacity must be at least one")

    def can_host(self, guests: int) -> bool:
        return self.status == RoomStatus.AVAILABLE and 0 < guests <= self.capacity


class BookingStatus(str, Enum):
    RESERVED = "reserved"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


@dataclass
class Booking:
    id: BookingId
    guest_id: GuestId
    room_id: RoomId
    stay: DateRange
    guests: int
    nightly_rate: Money
    status: BookingStatus = BookingStatus.RESERVED
    created_at: date = field(default_factory=date.today)
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def reserve(
        cls,
        guest_id: GuestId,
        room: Room,
        stay: DateRange,
        guests: int,
    ) -> "Booking":
        if not room.can_host(guests):
            raise ValidationError("Room cannot host the requested number of guests")
        booking = cls(
            id=BookingId.new(),
            guest_id=guest_id,
            room_id=room.id,
            stay=stay,
            guests=guests,
            nightly_rate=room.nightly_rate,
        )
        booking._events.append(
            BookingCreated(
                occurred_at=DomainEvent.now(),
                booking_id=booking.id,
                guest_id=guest_id,
                room_id=room.id,
                check_in=stay.check_in,
                check_out=stay.check_out,
            )
        )
        return booking

    @property
    def total(self) -> Money:
        return self.nightly_rate.multiply(self.stay.nights)

    def check_in(self, today: date) -> None:
        if self.status != BookingStatus.RESERVED:
            raise InvalidBookingStateError("Only reserved bookings can be checked in")
        if today < self.stay.check_in:
            raise InvalidBookingStateError("Cannot check in before the booking date")
        if today >= self.stay.check_out:
            raise InvalidBookingStateError("Cannot check in after the stay has ended")
        self.status = BookingStatus.CHECKED_IN
        self._events.append(
            BookingCheckedIn(
                occurred_at=DomainEvent.now(),
                booking_id=self.id,
                guest_id=self.guest_id,
                room_id=self.room_id,
                checked_in_on=today,
            )
        )

    def check_out(self, today: date) -> None:
        if self.status != BookingStatus.CHECKED_IN:
            raise InvalidBookingStateError("Only checked-in bookings can be checked out")
        if today < self.stay.check_in:
            raise InvalidBookingStateError("Cannot check out before the booking starts")
        self.status = BookingStatus.CHECKED_OUT
        self._events.append(
            BookingCheckedOut(
                occurred_at=DomainEvent.now(),
                booking_id=self.id,
                guest_id=self.guest_id,
                room_id=self.room_id,
                checked_out_on=today,
            )
        )

    def cancel(self) -> None:
        if self.status != BookingStatus.RESERVED:
            raise InvalidBookingStateError("Only reserved bookings can be cancelled")
        self.status = BookingStatus.CANCELLED

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events