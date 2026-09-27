from hotel_management.application.dto import RoomView
from hotel_management.application.ports import BookingRepository, RoomRepository, room_is_available
from hotel_management.domain.value_objects import DateRange, RoomId


class ListAvailableRooms:
    def __init__(self, rooms: RoomRepository, bookings: BookingRepository) -> None:
        self._rooms = rooms
        self._bookings = bookings

    def execute(self, check_in: str, check_out: str, guests: int) -> list[RoomView]:
        stay = DateRange.from_strings(check_in, check_out)
        result = []
        for room in self._rooms.list():
            available = room.can_host(guests) and room_is_available(
                room, stay, self._bookings.list_for_room(room.id)
            )
            result.append(RoomView.from_entity(room, available))
        return result
