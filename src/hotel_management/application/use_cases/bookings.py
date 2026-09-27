from __future__ import annotations

from hotel_management.application.dto import BookingView, CreateBookingCommand
from hotel_management.application.ports import (
    BookingUnitOfWork,
    BookingRepository,
    Clock,
    EventPublisher,
    GuestRepository,
    RoomRepository,
    room_is_available,
)
from hotel_management.domain.entities import Booking
from hotel_management.domain.exceptions import NotFoundError, RoomUnavailableError
from hotel_management.domain.value_objects import DateRange, GuestId, RoomId


class CreateBooking:
    def __init__(self, unit_of_work: BookingUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self, command: CreateBookingCommand) -> BookingView:
        with self._unit_of_work as transaction:
            guest_id = GuestId.from_string(command.guest_id)
            room_id = RoomId.from_string(command.room_id)
            guest = transaction.guests.get(guest_id)
            if guest is None:
                raise NotFoundError("Guest was not found")
            room = transaction.rooms.get(room_id)
            if room is None:
                raise NotFoundError("Room was not found")
            stay = DateRange.from_strings(command.check_in, command.check_out)
            if not room_is_available(
                room, stay, transaction.bookings.list_for_room(room.id)
            ):
                raise RoomUnavailableError("Room is not available for those dates")
            booking = Booking.reserve(guest.id, room, stay, command.guests)
            transaction.bookings.save(booking)
            transaction.events.publish(booking.pull_events())
            return BookingView.from_entity(booking)


class CheckInGuest:
    def __init__(self, unit_of_work: BookingUnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, booking_id: str) -> BookingView:
        with self._unit_of_work as transaction:
            booking = transaction.bookings.get(self._parse_id(booking_id))
            if booking is None:
                raise NotFoundError("Booking was not found")
            booking.check_in(self._clock.today())
            transaction.bookings.save(booking)
            transaction.events.publish(booking.pull_events())
            return BookingView.from_entity(booking)

    @staticmethod
    def _parse_id(booking_id: str):
        from hotel_management.domain.value_objects import BookingId

        return BookingId.from_string(booking_id)


class CheckOutGuest:
    def __init__(self, unit_of_work: BookingUnitOfWork, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, booking_id: str) -> BookingView:
        from hotel_management.domain.value_objects import BookingId

        with self._unit_of_work as transaction:
            booking = transaction.bookings.get(BookingId.from_string(booking_id))
            if booking is None:
                raise NotFoundError("Booking was not found")
            booking.check_out(self._clock.today())
            transaction.bookings.save(booking)
            transaction.events.publish(booking.pull_events())
            return BookingView.from_entity(booking)
