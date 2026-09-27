from __future__ import annotations

from dataclasses import dataclass
import os

from hotel_management.application.use_cases.bookings import (
    CheckInGuest,
    CheckOutGuest,
    CreateBooking,
)
from hotel_management.application.use_cases.guests import RegisterGuest
from hotel_management.application.use_cases.rooms import ListAvailableRooms
from hotel_management.infrastructure.persistence.in_memory import (
    InMemoryBookingRepository,
    InMemoryBookingUnitOfWork,
    InMemoryEventPublisher,
    InMemoryGuestRepository,
    InMemoryRoomRepository,
    SystemClock,
)
from hotel_management.infrastructure.seed import starter_rooms
from hotel_management.interfaces.http.controllers import HotelController


@dataclass
class Application:
    controller: HotelController
    guests: InMemoryGuestRepository
    rooms: InMemoryRoomRepository
    bookings: InMemoryBookingRepository
    events: InMemoryEventPublisher


def build_application() -> Application:
    if os.environ.get("HOTEL_STORAGE", "memory").lower() == "postgres":
        return build_postgres_application()
    return build_in_memory_application()


def build_in_memory_application() -> Application:
    guests = InMemoryGuestRepository()
    rooms = InMemoryRoomRepository(starter_rooms())
    bookings = InMemoryBookingRepository()
    events = InMemoryEventPublisher()
    unit_of_work = InMemoryBookingUnitOfWork(guests, rooms, bookings, events)
    clock = SystemClock()
    controller = HotelController(
        register_guest=RegisterGuest(guests),
        create_booking=CreateBooking(unit_of_work),
        list_available_rooms=ListAvailableRooms(rooms, bookings),
        check_in_guest=CheckInGuest(unit_of_work, clock),
        check_out_guest=CheckOutGuest(unit_of_work, clock),
    )
    return Application(controller, guests, rooms, bookings, events)


def build_postgres_application() -> Application:
    from hotel_management.infrastructure.configuration import PostgresSettings
    from hotel_management.infrastructure.persistence.postgres import (
        PostgresBookingRepository,
        PostgresBookingUnitOfWork,
        PostgresEventPublisher,
        PostgresGuestRepository,
        PostgresRoomRepository,
        psycopg_connection_factory,
    )

    connect = psycopg_connection_factory(PostgresSettings.from_environment().dsn)
    unit_of_work = PostgresBookingUnitOfWork(connect)
    guests = PostgresGuestRepository(connect)
    rooms = PostgresRoomRepository(connect)
    bookings = PostgresBookingRepository(connect)
    events = PostgresEventPublisher(connect)
    clock = SystemClock()
    controller = HotelController(
        register_guest=RegisterGuest(guests),
        create_booking=CreateBooking(unit_of_work),
        list_available_rooms=ListAvailableRooms(rooms, bookings),
        check_in_guest=CheckInGuest(unit_of_work, clock),
        check_out_guest=CheckOutGuest(unit_of_work, clock),
    )
    return Application(controller, guests, rooms, bookings, events)
