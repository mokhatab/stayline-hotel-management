from datetime import date
from decimal import Decimal
import unittest

from hotel_management.domain.entities import Booking, Room, RoomType
from hotel_management.domain.exceptions import InvalidBookingStateError, ValidationError
from hotel_management.domain.value_objects import DateRange, GuestId, Money, RoomId


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(RoomId.new(), "101", RoomType.DOUBLE, Money.from_amount("125"), 2)
        self.guest = GuestId.new()
        self.stay = DateRange(date(2026, 10, 1), date(2026, 10, 3))

    def test_date_range_is_half_open_and_counts_nights(self):
        self.assertEqual(self.stay.nights, 2)
        self.assertFalse(self.stay.overlaps(DateRange(date(2026, 10, 3), date(2026, 10, 4))))

    def test_booking_total_and_event_are_created_by_domain(self):
        booking = Booking.reserve(self.guest, self.room, self.stay, 2)
        self.assertEqual(booking.total.amount, Decimal("250.00"))
        self.assertEqual(len(booking.pull_events()), 1)

    def test_room_rejects_more_guests_than_capacity(self):
        with self.assertRaises(ValidationError):
            Booking.reserve(self.guest, self.room, self.stay, 3)

    def test_booking_cannot_check_in_before_arrival(self):
        booking = Booking.reserve(self.guest, self.room, self.stay, 1)
        with self.assertRaises(InvalidBookingStateError):
            booking.check_in(date(2026, 9, 30))

    def test_booking_can_transition_through_stay(self):
        booking = Booking.reserve(self.guest, self.room, self.stay, 1)
        booking.pull_events()
        booking.check_in(date(2026, 10, 1))
        self.assertEqual(type(booking.pull_events()[0]).__name__, "BookingCheckedIn")
        booking.check_out(date(2026, 10, 2))
        self.assertEqual(type(booking.pull_events()[0]).__name__, "BookingCheckedOut")
        self.assertEqual(booking.status.value, "checked_out")


if __name__ == "__main__":
    unittest.main()
