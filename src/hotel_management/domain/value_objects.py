from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from .exceptions import ValidationError


@dataclass(frozen=True)
class GuestId:
    value: UUID

    @classmethod
    def new(cls) -> "GuestId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "GuestId":
        try:
            return cls(UUID(value))
        except (ValueError, AttributeError) as error:
            raise ValidationError("Guest id must be a valid UUID") from error

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class RoomId:
    value: UUID

    @classmethod
    def new(cls) -> "RoomId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "RoomId":
        try:
            return cls(UUID(value))
        except (ValueError, AttributeError) as error:
            raise ValidationError("Room id must be a valid UUID") from error

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BookingId:
    value: UUID

    @classmethod
    def new(cls) -> "BookingId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "BookingId":
        try:
            return cls(UUID(value))
        except (ValueError, AttributeError) as error:
            raise ValidationError("Booking id must be a valid UUID") from error

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class DateRange:
    check_in: date
    check_out: date

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:
            raise ValidationError("Check-out must be after check-in")

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    def overlaps(self, other: "DateRange") -> bool:
        return self.check_in < other.check_out and other.check_in < self.check_out

    @classmethod
    def from_strings(cls, check_in: str, check_out: str) -> "DateRange":
        try:
            return cls(date.fromisoformat(check_in), date.fromisoformat(check_out))
        except (TypeError, ValueError) as error:
            raise ValidationError("Dates must use YYYY-MM-DD format") from error


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValidationError("Money amount cannot be negative")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError("Currency must be a three-letter code")

    @classmethod
    def from_amount(cls, amount: str | int | float, currency: str = "USD") -> "Money":
        try:
            return cls(Decimal(str(amount)).quantize(Decimal("0.01")), currency.upper())
        except Exception as error:
            raise ValidationError("Amount must be a valid number") from error

    def multiply(self, quantity: int) -> "Money":
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative")
        return Money((self.amount * quantity).quantize(Decimal("0.01")), self.currency)
