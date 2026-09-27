from hotel_management.application.dto import CreateGuestCommand
from hotel_management.application.ports import GuestRepository
from hotel_management.domain.entities import Guest
from hotel_management.domain.value_objects import GuestId


class RegisterGuest:
    def __init__(self, guests: GuestRepository) -> None:
        self._guests = guests

    def execute(self, command: CreateGuestCommand) -> Guest:
        guest = Guest(
            id=GuestId.new(),
            full_name=command.full_name,
            email=command.email,
            phone=command.phone,
        )
        self._guests.save(guest)
        return guest
