from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
import json

from hotel_management.application.dto import CreateBookingCommand, CreateGuestCommand
from hotel_management.application.use_cases.bookings import (
    CheckInGuest,
    CheckOutGuest,
    CreateBooking,
)
from hotel_management.application.use_cases.guests import RegisterGuest
from hotel_management.application.use_cases.rooms import ListAvailableRooms
from hotel_management.domain.entities import Guest
from hotel_management.domain.exceptions import DomainError


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize(value) -> dict | list:
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {key: _json_value(serialize(item)) for key, item in asdict(value).items()}
    return value


class HotelController:
    def __init__(
        self,
        register_guest: RegisterGuest,
        create_booking: CreateBooking,
        list_available_rooms: ListAvailableRooms,
        check_in_guest: CheckInGuest,
        check_out_guest: CheckOutGuest,
    ) -> None:
        self._register_guest = register_guest
        self._create_booking = create_booking
        self._list_available_rooms = list_available_rooms
        self._check_in_guest = check_in_guest
        self._check_out_guest = check_out_guest

    def register_guest(self, payload: dict) -> tuple[int, dict]:
        guest = self._register_guest.execute(
            CreateGuestCommand(
                full_name=payload.get("full_name", ""),
                email=payload.get("email", ""),
                phone=payload.get("phone"),
            )
        )
        return 201, {
            "id": str(guest.id),
            "full_name": guest.full_name,
            "email": guest.email,
            "phone": guest.phone,
        }

    def create_booking(self, payload: dict) -> tuple[int, dict]:
        booking = self._create_booking.execute(
            CreateBookingCommand(
                guest_id=payload.get("guest_id", ""),
                room_id=payload.get("room_id", ""),
                check_in=payload.get("check_in", ""),
                check_out=payload.get("check_out", ""),
                guests=int(payload.get("guests", 0)),
            )
        )
        return 201, serialize(booking)

    def list_rooms(self, query: dict) -> tuple[int, list]:
        rooms = self._list_available_rooms.execute(
            query.get("check_in", ""),
            query.get("check_out", ""),
            int(query.get("guests", 1)),
        )
        return 200, serialize(rooms)

    def check_in(self, booking_id: str) -> tuple[int, dict]:
        return 200, serialize(self._check_in_guest.execute(booking_id))

    def check_out(self, booking_id: str) -> tuple[int, dict]:
        return 200, serialize(self._check_out_guest.execute(booking_id))

    @staticmethod
    def error(error: Exception) -> tuple[int, dict]:
        if isinstance(error, DomainError):
            status = 404 if error.__class__.__name__ == "NotFoundError" else 422
            return status, {"error": str(error)}
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return 400, {"error": "Request payload is invalid"}
        return 500, {"error": "Internal server error"}

    @staticmethod
    def encode(payload) -> bytes:
        return json.dumps(payload).encode("utf-8")
