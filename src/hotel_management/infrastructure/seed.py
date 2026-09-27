from hotel_management.domain.entities import Room, RoomType
from hotel_management.domain.value_objects import Money, RoomId


def starter_rooms() -> list[Room]:
    return [
        Room(RoomId.new(), "101", RoomType.SINGLE, Money.from_amount("85"), 1),
        Room(RoomId.new(), "202", RoomType.DOUBLE, Money.from_amount("125"), 2),
        Room(RoomId.new(), "303", RoomType.SUITE, Money.from_amount("220"), 4),
    ]
