import unittest

from hotel_management.application.dto import CreateBookingCommand, CreateGuestCommand
from hotel_management.application.use_cases.bookings import CreateBooking
from hotel_management.application.use_cases.guests import RegisterGuest
from hotel_management.application.use_cases.rooms import ListAvailableRooms
from hotel_management.domain.exceptions import RoomUnavailableError
from hotel_management.infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryBookingUnitOfWork,
    InMemoryEventPublisher,
    InMemoryGuestRepository,
    InMemoryRoomRepository,
)
from hotel_management.infrastructure.seed import starter_rooms


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.guests = InMemoryGuestRepository()
        self.rooms = InMemoryRoomRepository(starter_rooms())
        self.bookings = InMemoryBookingRepository()
        self.events = InMemoryEventPublisher()
        self.unit_of_work = InMemoryBookingUnitOfWork(
            self.guests, self.rooms, self.bookings, self.events
        )
        self.register_guest = RegisterGuest(self.guests)
        self.create_booking = CreateBooking(self.unit_of_work)
        self.guest = self.register_guest.execute(
            CreateGuestCommand("Ada Lovelace", "ada@example.com")
        )
        self.room = self.rooms.list()[0]

    def command(self, room_id=None):
        return CreateBookingCommand(
            guest_id=str(self.guest.id),
            room_id=str(room_id or self.room.id),
            check_in="2026-10-01",
            check_out="2026-10-03",
            guests=1,
        )

    def test_create_booking_uses_ports_and_publishes_event(self):
        result = self.create_booking.execute(self.command())
        self.assertEqual(result.nights, 2)
        self.assertEqual(result.status, "reserved")
        self.assertEqual(len(self.events.published), 1)

    def test_overlapping_booking_is_rejected(self):
        self.create_booking.execute(self.command())
        with self.assertRaises(RoomUnavailableError):
            self.create_booking.execute(self.command())

    def test_booking_transaction_rolls_back_when_event_publishing_fails(self):
        def fail_to_publish(events):
            raise RuntimeError("outbox unavailable")

        self.events.publish = fail_to_publish
        with self.assertRaises(RuntimeError):
            self.create_booking.execute(self.command())
        self.assertEqual(self.bookings.list_for_room(self.room.id), [])

    def test_availability_query_keeps_room_in_inventory_but_marks_it_unavailable(self):
        self.create_booking.execute(self.command())
        rooms = ListAvailableRooms(self.rooms, self.bookings).execute(
            "2026-10-01", "2026-10-03", 1
        )
        matching = next(room for room in rooms if room.id == str(self.room.id))
        self.assertFalse(matching.available)


if __name__ == "__main__":
    unittest.main()
