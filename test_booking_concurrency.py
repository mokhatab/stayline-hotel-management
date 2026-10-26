"""Concurrency test against a real PostgreSQL database.

Skipped unless HOTEL_TEST_DATABASE_URL is set. The test TRUNCATES the hotel
tables, so point it at a throwaway database, never at production data.

    HOTEL_TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/stayline_test \
        PYTHONPATH=src python -m unittest tests.test_booking_concurrency -v
"""

from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import threading
import unittest

from hotel_management.application.dto import CreateBookingCommand
from hotel_management.application.use_cases.bookings import CreateBooking
from hotel_management.domain.entities import Guest, Room, RoomType
from hotel_management.domain.exceptions import RoomUnavailableError
from hotel_management.domain.value_objects import GuestId, Money, RoomId

DSN = os.environ.get("HOTEL_TEST_DATABASE_URL")
SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "src/hotel_management/infrastructure/persistence/schema.sql"
)

CONCURRENT_REQUESTS = 8
ROUNDS = 15


@unittest.skipUnless(DSN, "HOTEL_TEST_DATABASE_URL is not set")
class BookingConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import psycopg

        from hotel_management.infrastructure.persistence.postgres import (
            PostgresBookingUnitOfWork,
            PostgresGuestRepository,
            PostgresRoomRepository,
            psycopg_connection_factory,
        )

        cls.psycopg = psycopg
        cls.connect = staticmethod(psycopg_connection_factory(DSN))
        cls.unit_of_work_class = PostgresBookingUnitOfWork
        cls.guest_repository = PostgresGuestRepository(cls.connect)
        cls.room_repository = PostgresRoomRepository(cls.connect)
        with psycopg.connect(DSN) as connection:
            connection.execute(SCHEMA.read_text())
            connection.execute(
                "TRUNCATE bookings, domain_events, guests, rooms RESTART IDENTITY CASCADE"
            )

    def _seed_room_and_guest(self, number: str) -> tuple[Room, Guest]:
        guest = Guest(GuestId.new(), "Grace Hopper", f"grace{number}@example.com")
        self.guest_repository.save(guest)
        room = Room(
            RoomId.new(), number, RoomType.DOUBLE, Money(Decimal("125.00")), 2
        )
        with self.psycopg.connect(DSN) as connection:
            connection.execute(
                "INSERT INTO rooms (id, number, room_type, nightly_rate, capacity,"
                " currency, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    room.id.value,
                    room.number,
                    room.room_type.value,
                    room.nightly_rate.amount,
                    room.capacity,
                    room.nightly_rate.currency,
                    room.status.value,
                ),
            )
        return room, guest

    def test_simultaneous_requests_for_one_room_book_it_exactly_once(self) -> None:
        double_booked_rounds = []
        for round_number in range(ROUNDS):
            room, guest = self._seed_room_and_guest(f"R{round_number}")
            command = CreateBookingCommand(
                guest_id=str(guest.id.value),
                room_id=str(room.id.value),
                check_in="2027-03-01",
                check_out="2027-03-03",
                guests=2,
            )
            barrier = threading.Barrier(CONCURRENT_REQUESTS)
            outcomes: list[str] = []
            lock = threading.Lock()

            def attempt() -> None:
                # Each request gets its own unit of work, like separate processes.
                use_case = CreateBooking(self.unit_of_work_class(self.connect))
                barrier.wait()
                try:
                    use_case.execute(command)
                    result = "booked"
                except RoomUnavailableError:
                    result = "unavailable"
                except Exception as error:  # surfaced below, never hidden
                    result = f"error: {type(error).__name__}: {error}"
                with lock:
                    outcomes.append(result)

            threads = [
                threading.Thread(target=attempt) for _ in range(CONCURRENT_REQUESTS)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            with self.psycopg.connect(DSN) as connection:
                stored = connection.execute(
                    "SELECT count(*) FROM bookings WHERE room_id = %s"
                    " AND status IN ('reserved', 'checked_in')",
                    (room.id.value,),
                ).fetchone()[0]

            unexpected = [o for o in outcomes if o.startswith("error")]
            self.assertEqual(unexpected, [], "unexpected errors during booking")
            if outcomes.count("booked") != 1 or stored != 1:
                double_booked_rounds.append(
                    (round_number, outcomes.count("booked"), stored)
                )

        self.assertEqual(
            double_booked_rounds,
            [],
            "rounds where the room was booked more than once "
            "(round, successful requests, rows stored)",
        )


if __name__ == "__main__":
    unittest.main()
